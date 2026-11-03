//! Local-first pre-submission evidence (D034): a bounded TCP connect to the
//! configured LiteLLM endpoint. It sends no bytes, credentials or HTTP request.
use std::net::{SocketAddr, TcpStream, ToSocketAddrs};
use std::time::Duration;
use tokio::time::Instant;

pub(crate) const BUDGET: Duration = Duration::from_secs(5);

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum Reachability {
    Reachable,
    /// Name resolution failed, or every address refused, was unreachable or
    /// timed out: confirmed transport failure before any coding attempt.
    Unreachable,
    /// Any other local error; never eligible evidence.
    Unknown,
    /// Cancellation or the overall deadline ended the check.
    Stopped,
}

/// A plain worker thread keeps resolver/connect calls outside Tokio's blocking
/// pool, so dropping it after the budget never delays runtime shutdown.
pub(crate) async fn litellm(
    api_base: &str,
    deadline: Instant,
    cancelled: &tokio_util::sync::CancellationToken,
) -> Reachability {
    let Ok(endpoint) = url::Url::parse(api_base) else {
        return Reachability::Unknown;
    };
    let (Some(host), Some(port)) = (endpoint.host(), endpoint.port_or_known_default()) else {
        return Reachability::Unknown;
    };
    let host = host.to_owned();
    let budget = deadline.min(Instant::now() + BUDGET);
    let limit = budget.into_std();
    let (send, receive) = tokio::sync::oneshot::channel();
    let worker = std::thread::Builder::new()
        .name("ah-litellm-probe".into())
        .spawn(move || {
            let addresses: Vec<SocketAddr> = match &host {
                url::Host::Domain(name) => match (name.as_str(), port).to_socket_addrs() {
                    Ok(found) => found.collect(),
                    Err(_) => Vec::new(),
                },
                url::Host::Ipv4(ip) => vec![SocketAddr::from((*ip, port))],
                url::Host::Ipv6(ip) => vec![SocketAddr::from((*ip, port))],
            };
            let _ = send.send(connect(&addresses, limit));
        });
    if worker.is_err() {
        return Reachability::Unknown;
    }
    let found = tokio::select! {
        result = tokio::time::timeout_at(budget, receive) => match result {
            Ok(Ok(found)) => found,
            Ok(Err(_)) => Reachability::Unknown,
            Err(_) => Reachability::Unreachable,
        },
        _ = cancelled.cancelled() => Reachability::Stopped,
    };
    // Cancellation and deadline take precedence over any concurrent result.
    if cancelled.is_cancelled() || Instant::now() >= deadline {
        return Reachability::Stopped;
    }
    found
}

fn connect(addresses: &[SocketAddr], limit: std::time::Instant) -> Reachability {
    use std::io::ErrorKind::*;
    let mut result = Reachability::Unreachable;
    for address in addresses {
        let Some(left) = limit
            .checked_duration_since(std::time::Instant::now())
            .filter(|d| !d.is_zero())
        else {
            break;
        };
        match TcpStream::connect_timeout(address, left) {
            // Dropped immediately: no request bytes are written.
            Ok(_) => return Reachability::Reachable,
            Err(e)
                if matches!(
                    e.kind(),
                    ConnectionRefused | HostUnreachable | NetworkUnreachable | TimedOut
                ) => {}
            Err(_) => result = Reachability::Unknown,
        }
    }
    result
}

#[cfg(test)]
mod tests {
    use super::{Reachability, litellm};
    use std::time::Duration;
    use tokio::time::Instant;

    async fn check(api_base: &str) -> Reachability {
        let token = tokio_util::sync::CancellationToken::new();
        litellm(api_base, Instant::now() + Duration::from_secs(10), &token).await
    }

    #[tokio::test]
    async fn listening_endpoint_is_reachable_and_receives_no_bytes() {
        use std::io::Read;
        let listener = std::net::TcpListener::bind("127.0.0.1:0").unwrap();
        let port = listener.local_addr().unwrap().port();
        let reachability = check(&format!("http://127.0.0.1:{port}/v1")).await;
        assert_eq!(reachability, Reachability::Reachable);
        let (mut accepted, _) = listener.accept().unwrap();
        let mut bytes = Vec::new();
        accepted.read_to_end(&mut bytes).unwrap();
        assert!(bytes.is_empty());
    }

    #[tokio::test]
    async fn refused_or_unresolvable_endpoint_is_unreachable() {
        let port = std::net::TcpListener::bind("127.0.0.1:0")
            .unwrap()
            .local_addr()
            .unwrap()
            .port();
        assert_eq!(
            check(&format!("http://127.0.0.1:{port}/v1")).await,
            Reachability::Unreachable
        );
        assert_eq!(
            check(&format!("http://[::1]:{port}/v1")).await,
            Reachability::Unreachable
        );
        assert_eq!(
            check("http://ah-unresolvable.invalid:4000/v1").await,
            Reachability::Unreachable
        );
    }

    #[tokio::test]
    async fn cancellation_and_expired_deadline_stop_the_check() {
        let token = tokio_util::sync::CancellationToken::new();
        token.cancel();
        let far = Instant::now() + Duration::from_secs(10);
        // A non-routable address would otherwise wait for the whole budget.
        assert_eq!(
            litellm("http://10.255.255.1:4000/v1", far, &token).await,
            Reachability::Stopped
        );
        let fresh = tokio_util::sync::CancellationToken::new();
        assert_eq!(
            litellm("http://10.255.255.1:4000/v1", Instant::now(), &fresh).await,
            Reachability::Stopped
        );
    }
}
