//! Pinned OpenCode 2.2.5 runtime surface (D035): native-schema config for both
//! routes, project agent emission, named-role mapping (D038), and pure
//! validators for its configuration sources, agents and catalog.
use crate::agents::{self, Agent, Capacity, Effort, Tool};
use crate::config::{Invalid, Mode, Permissions, Resolved};
use serde_json::{Value, json};
use std::path::Path;

pub(crate) const VERSION: &str = "2.2.5";
const LOCAL: &str = "ah-litellm";
const NATIVE: &str = "opencode";

fn provider(request: &Resolved) -> &'static str {
    if request.mode == Mode::LocalOnly {
        LOCAL
    } else {
        NATIVE
    }
}

/// Model reference in the 2.x `{providerID, model}` form.
pub(crate) fn model(request: &Resolved) -> Value {
    json!({"providerID": provider(request), "model": request.model})
}

fn rule(action: &str, effect: &str) -> Value {
    json!({"action": action, "resource": "*", "effect": effect})
}

/// Ordered rules; OpenCode appends them after each agent's built-in defaults
/// and evaluates the last match. Deny removes the tools from the model.
pub(crate) fn profile(policy: Permissions) -> Value {
    let mut rules = vec![rule("*", "deny")];
    if policy == Permissions::Trusted {
        for action in ["read", "glob", "grep", "edit", "shell"] {
            rules.push(rule(action, "ask"));
        }
    }
    rules.push(rule(
        "external_directory",
        if policy == Permissions::Trusted {
            "ask"
        } else {
            "deny"
        },
    ));
    Value::Array(rules)
}

/// Static rules for an emitted project agent: only the canonical ceiling and
/// tool list, each listed tool `ask`, never `allow`. A full trusted tool set
/// equals the trusted profile; an empty deny/read-only set equals the deny
/// profile, while trusted still asks for `external_directory`. This is not
/// the enforced runtime entry, which must also intersect invocation (P4.3).
pub(crate) fn ceiling(agent: &Agent) -> Value {
    let mut rules = vec![rule("*", "deny")];
    for (tool, actions) in [
        (Tool::Read, &["read"][..]),
        (Tool::Search, &["glob", "grep"]),
        (Tool::Edit, &["edit"]),
        (Tool::Execute, &["shell"]),
    ] {
        if agent.tools().contains(&tool) {
            rules.extend(actions.iter().map(|action| rule(action, "ask")));
        }
    }
    rules.push(rule(
        "external_directory",
        if agent.permissions() == agents::Permissions::Trusted {
            "ask"
        } else {
            "deny"
        },
    ));
    Value::Array(rules)
}

/// Enforced runtime rules: the invocation profile intersected with a selected
/// agent's ceiling and tools. A deny invocation keeps the deny profile; a
/// trusted one narrows to the agent's rules, never wider than trusted.
pub(crate) fn effective(request: &Resolved) -> Value {
    match (&request.agent, request.permissions) {
        (Some(agent), Permissions::Trusted) => ceiling(agent),
        (_, policy) => profile(policy),
    }
}

/// ACP tool kinds the harness may grant once under the effective rules;
/// empty when no tool can run. Mirrors the `ceiling` tool mapping.
pub(crate) fn grantable(request: &Resolved) -> Vec<&'static str> {
    if request.permissions != Permissions::Trusted {
        return Vec::new();
    }
    let all = [Tool::Read, Tool::Search, Tool::Edit, Tool::Execute];
    let tools = request.agent.as_ref().map_or(&all[..], Agent::tools);
    tools
        .iter()
        .map(|tool| match tool {
            Tool::Read => "read",
            Tool::Search => "search",
            Tool::Edit => "edit",
            Tool::Execute => "execute",
        })
        .collect()
}

/// Required capabilities the pinned runtime cannot enforce. 2.2.5 advertises
/// an `effort` session option, but no mapping to provider requests has been
/// verified, so only `default` is supported (D038).
pub(crate) fn supports(agent: &Agent) -> Result<(), Invalid> {
    if agent.effort() == Effort::Default {
        Ok(())
    } else {
        Err(Invalid(
            "agent effort is unsupported by OpenCode 2.2.5; only default effort runs",
        ))
    }
}

/// 2.2.5 runs a prompt whose first word is `/NAME` as a runtime command
/// (ACP advertises built-ins `init`, `review`, `goal` and `compact`; project
/// commands are not loaded). Such a turn can report `end_turn` with an empty
/// response and no model request, so command prompts are unsupported (D040).
/// A leading path such as `/src/main.rs` (with a second `/`) remains text.
pub(crate) fn prompt_supported(prompt: &str) -> Result<(), Invalid> {
    let word = prompt.split_whitespace().next().unwrap_or_default();
    match word.strip_prefix('/') {
        Some(name) if !name.is_empty() && !name.contains('/') => Err(Invalid(
            "prompt starts with a runtime slash command, which is unsupported; rephrase it",
        )),
        _ => Ok(()),
    }
}

/// Project `.opencode/agents/NAME.md` for direct OpenCode use on the local
/// route (D037): native frontmatter as one JSON flow mapping, which is valid
/// YAML, then the canonical Markdown body unchanged as `system`.
pub(crate) fn agent_markdown(agent: &Agent, request: &Resolved) -> String {
    let mode = match agent.capacity() {
        Capacity::Primary => "primary",
        Capacity::Specialized => "subagent",
        Capacity::Both => "all",
    };
    let header = json!({
        "description": agent.description(),
        "mode": mode,
        "model": model(request),
        "permissions": ceiling(agent),
    });
    format!("---\n{header}\n---\n{}", agent.body())
}

/// Complete runtime configuration passed via OPENCODE_CONFIG_CONTENT. Only the
/// selected provider may be used; the title helper is pinned to the same model.
/// Project instructions are the one absolute `AGENTS.md` path, or none: 2.2.5
/// loads no project instructions with project configuration disabled (D040).
/// Skills, MCP servers and plugins stay empty or denied by the rules.
/// Global rules are the effective rules, so built-in helpers and subagents
/// never exceed a selected agent. The harness invokes that agent directly as
/// the default agent, so its entry is always `primary`: 2.2.5 silently falls
/// back to `build` for a `subagent` default (D038).
pub(crate) fn config(request: &Resolved) -> Value {
    let provider = provider(request);
    let providers = if request.mode == Mode::LocalOnly {
        json!({LOCAL: {
            "package": "aisdk:@ai-sdk/openai-compatible",
            "settings": {"apiKey": "{env:AH_RUNTIME_API_KEY}", "baseURL": request.api_base},
            "models": {&request.model: {"name": request.model}},
        }})
    } else {
        json!({})
    };
    let mut agents = json!({"title": {"model": model(request)}});
    if let Some(agent) = &request.agent {
        agents[agent.name()] = json!({
            "description": agent.description(),
            "mode": "primary",
            "model": model(request),
            "permissions": effective(request),
            "system": agent.body(),
        });
    }
    json!({
        "model": model(request),
        "default_agent": request.agent.as_ref().map_or("build", Agent::name),
        "update": "disable",
        "share": "disabled",
        "permissions": effective(request),
        "policies": [
            {"action": "provider.use", "resource": "*", "effect": "deny"},
            {"action": "provider.use", "resource": provider, "effect": "allow"},
        ],
        "agents": agents,
        "instructions": request.instructions.iter().collect::<Vec<_>>(),
        "mcp": {},
        "plugins": [],
        "providers": providers,
    })
}

/// `debug config` lists sources rather than a merged view. Exactly the private
/// config directory and the supplied document may contribute; the document must
/// echo what was sent, with only the resolved credential masked.
pub(crate) fn validate_sources(sent: &Value, sources: &Value, home: &Path) -> Result<(), Invalid> {
    const DIFFERS: Invalid =
        Invalid("effective runtime configuration sources differ from the selected route");
    let [directory, document] = sources.as_array().map(Vec::as_slice).unwrap_or_default() else {
        return Err(DIFFERS);
    };
    let expected = home.join("CONFIG").join("opencode");
    let same_directory = directory.as_object().is_some_and(|d| d.len() == 2)
        && directory["type"] == "directory"
        && directory["path"].as_str().is_some_and(|path| {
            matches!((Path::new(path).canonicalize(), expected.canonicalize()), (Ok(a), Ok(b)) if a == b)
        });
    let mut masked = sent.clone();
    if let Some(providers) = masked["providers"].as_object_mut() {
        for provider in providers.values_mut() {
            provider["settings"]["apiKey"] = json!("***");
        }
    }
    let same_document = document.as_object().is_some_and(|d| d.len() == 2)
        && document["type"] == "document"
        && document["info"] == masked;
    if same_directory && same_document {
        Ok(())
    } else {
        Err(DIFFERS)
    }
}

/// Every agent, including built-in helpers and subagents, must end with the
/// effective rules followed only by built-in denials, use no other model and
/// carry no request overrides. The default agent (`build`, or the selected
/// agent with its exact model and system text) must be a visible primary.
pub(crate) fn validate_agents(request: &Resolved, agents: &Value) -> Result<(), Invalid> {
    const DIFFERS: Invalid =
        Invalid("effective agents differ from the selected route or permissions");
    let profile = effective(request);
    let profile = profile.as_array().expect("profile is an array");
    let wanted = json!({"id": request.model, "providerID": provider(request)});
    let agents = agents.as_array().ok_or(DIFFERS)?;
    let mut default = false;
    for agent in agents {
        let rules = agent["permissions"].as_array().ok_or(DIFFERS)?;
        let start = rules
            .windows(profile.len())
            .rposition(|window| window == profile.as_slice())
            .ok_or(DIFFERS)?;
        if !rules[start + profile.len()..]
            .iter()
            .all(|rule| rule["effect"] == "deny")
            || !(agent["model"].is_null() || agent["model"] == wanted)
            || agent["request"] != json!({"settings": {}, "headers": {}, "body": {}})
        {
            return Err(DIFFERS);
        }
        let visible = agent["mode"] == "primary" && agent["hidden"] == false;
        default |= match &request.agent {
            None => agent["id"] == "build" && visible,
            Some(named) => {
                agent["id"] == named.name()
                    && visible
                    && agent["model"] == wanted
                    && agent["system"] == named.body()
                    && agent["description"] == named.description()
            }
        };
    }
    if default { Ok(()) } else { Err(DIFFERS) }
}

/// Built-in catalog only: the provider policy must hide every other provider.
/// This checks support, not credential validity or balance.
pub(crate) fn validate_catalog(request: &Resolved, models: &str) -> Result<(), Invalid> {
    let target = request.runtime_model();
    if models.lines().any(|line| line == target)
        && models.lines().all(|line| line.starts_with("opencode/"))
    {
        Ok(())
    } else {
        Err(Invalid("native catalog differs from the built-in target"))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn request(mode: Mode, permissions: Permissions) -> Resolved {
        let config = if mode == Mode::LocalOnly {
            r#"{"version":1,"mode":"local-only","model":"proxy","litellm":{"api_base":"http://litellm:4000/v1","api_key_env":"KEY"}}"#
        } else {
            r#"{"version":1,"mode":"cloud-only","native":{"target":"opencode","model":"gpt-5.4","api_key_env":"KEY"}}"#
        };
        let mut args = vec!["single".into(), "task".into()];
        if permissions == Permissions::Trusted {
            args.extend(["--permissions".into(), "trusted".into()]);
        }
        crate::config::Invocation::parse(args, Path::new("/tmp"))
            .unwrap()
            .resolve(
                crate::config::Config::read(config.as_bytes()).unwrap(),
                |_| Some("SECRET".into()),
                &b""[..],
            )
            .unwrap()
    }

    fn agent(id: &str, rules: Vec<Value>, model: Value) -> Value {
        json!({"id": id, "mode": "primary", "hidden": false, "model": model, "permissions": rules,
               "request": {"settings": {}, "headers": {}, "body": {}}})
    }

    fn rules(request: &Resolved, tail: &[Value]) -> Vec<Value> {
        let mut rules = vec![json!({"action": "*", "resource": "*", "effect": "allow"})];
        rules.extend(
            profile(request.permissions)
                .as_array()
                .unwrap()
                .iter()
                .cloned(),
        );
        rules.extend(tail.iter().cloned());
        rules
    }

    #[test]
    fn config_selects_only_the_route_provider_and_model() {
        let local = config(&request(Mode::LocalOnly, Permissions::Deny));
        assert_eq!(
            local["model"],
            json!({"providerID": "ah-litellm", "model": "proxy"})
        );
        assert_eq!(local["agents"]["title"]["model"], local["model"]);
        assert_eq!(local["policies"][1]["resource"], "ah-litellm");
        assert_eq!(
            local["providers"]["ah-litellm"]["settings"]["apiKey"],
            "{env:AH_RUNTIME_API_KEY}"
        );
        assert!(!local.to_string().contains("SECRET"));
        let native = config(&request(Mode::CloudOnly, Permissions::Deny));
        assert_eq!(
            native["model"],
            json!({"providerID": "opencode", "model": "gpt-5.4"})
        );
        assert_eq!(native["providers"], json!({}));
        assert!(!native.to_string().contains("litellm"));
        let trusted = profile(Permissions::Trusted);
        assert_eq!(
            trusted[0],
            json!({"action": "*", "resource": "*", "effect": "deny"})
        );
        assert!(
            trusted
                .as_array()
                .unwrap()
                .iter()
                .all(|r| r["effect"] != "allow")
        );
    }

    #[test]
    fn sources_must_be_exactly_private_directory_and_masked_document() {
        let home = tempfile_home();
        let r = request(Mode::LocalOnly, Permissions::Deny);
        let sent = config(&r);
        let mut info = sent.clone();
        info["providers"]["ah-litellm"]["settings"]["apiKey"] = json!("***");
        let directory = json!({"type": "directory", "path": home.join("CONFIG/opencode")});
        let good = json!([directory, {"type": "document", "info": info}]);
        validate_sources(&sent, &good, &home).unwrap();
        let mut project = good.clone();
        project.as_array_mut().unwrap().insert(
            1,
            json!({"type": "document", "path": "/p/opencode.json", "info": {}}),
        );
        let mut changed = good.clone();
        changed[1]["info"]["agents"]["helper"] =
            json!({"model": {"providerID": "other", "model": "x"}});
        let mut unmasked = good.clone();
        unmasked[1]["info"] = sent.clone();
        let mut elsewhere = good.clone();
        elsewhere[0]["path"] = json!("/tmp");
        for bad in [project, changed, unmasked, elsewhere, json!([]), json!({})] {
            assert!(validate_sources(&sent, &bad, &home).is_err(), "{bad}");
        }
        std::fs::remove_dir_all(home).unwrap();
    }

    fn tempfile_home() -> std::path::PathBuf {
        let home = std::env::temp_dir().join(format!("ah-opencode-test-{}", std::process::id()));
        std::fs::create_dir_all(home.join("CONFIG/opencode")).unwrap();
        home
    }

    #[test]
    fn every_agent_ends_with_the_profile_and_selected_model() {
        for permissions in [Permissions::Deny, Permissions::Trusted] {
            let r = request(Mode::CloudOnly, permissions);
            let deny = json!({"action": "browser", "resource": "*", "effect": "deny"});
            let model = json!({"id": "gpt-5.4", "providerID": "opencode"});
            let good = json!([
                agent("build", rules(&r, &[deny.clone()]), Value::Null),
                agent("title", rules(&r, &[]), model.clone())
            ]);
            validate_agents(&r, &good).unwrap();
            let allow = json!({"action": "shell", "resource": "*", "effect": "allow"});
            let ask = json!({"action": "edit", "resource": "*", "effect": "ask"});
            let mut overridden = agent("build", rules(&r, &[]), Value::Null);
            overridden["request"]["body"] = json!({"model": "other"});
            for bad in [
                json!([agent("build", rules(&r, &[allow.clone()]), Value::Null)]),
                json!([
                    agent("build", rules(&r, &[]), Value::Null),
                    agent("explore", rules(&r, &[ask.clone()]), Value::Null)
                ]),
                json!([agent(
                    "build",
                    rules(&r, &[]),
                    json!({"id": "other", "providerID": "opencode"})
                )]),
                json!([agent(
                    "build",
                    vec![json!({"action": "*", "resource": "*", "effect": "allow"})],
                    Value::Null
                )]),
                json!([agent("title", rules(&r, &[]), model.clone())]),
                json!([overridden]),
            ] {
                assert!(validate_agents(&r, &bad).is_err(), "{bad}");
            }
        }
    }

    #[test]
    fn ceiling_never_allows_and_matches_profiles_at_the_extremes() {
        let agent = |permissions: &str, tools: &str| {
            Agent::read(format!("---\nversion: 1\nname: x\ndescription: d\ncapacity: primary\npermissions: {permissions}\ntools: {tools}\n---\nb\n").as_bytes()).unwrap()
        };
        let full = agent("trusted", "[execute, edit, search, read]");
        assert_eq!(ceiling(&full), profile(Permissions::Trusted));
        assert_eq!(ceiling(&agent("deny", "[]")), profile(Permissions::Deny));
        assert_eq!(
            ceiling(&agent("read-only", "[]")),
            profile(Permissions::Deny)
        );
        let trusted_empty = ceiling(&agent("trusted", "[]"));
        assert_ne!(trusted_empty, profile(Permissions::Deny));
        assert_eq!(trusted_empty.as_array().unwrap().len(), 2);
        assert_eq!(trusted_empty[1]["action"], "external_directory");
        assert_eq!(trusted_empty[1]["effect"], "ask");
        let read_only = ceiling(&agent("read-only", "[search]"));
        let actions: Vec<_> = read_only
            .as_array()
            .unwrap()
            .iter()
            .map(|r| (r["action"].as_str().unwrap(), r["effect"].as_str().unwrap()))
            .collect();
        assert_eq!(
            actions,
            [
                ("*", "deny"),
                ("glob", "ask"),
                ("grep", "ask"),
                ("external_directory", "deny")
            ]
        );
        assert!(
            !agent_markdown(&full, &request(Mode::LocalOnly, Permissions::Deny)).contains("allow")
        );
    }

    fn named(permissions: Permissions, ceiling: &str, tools: &str) -> Resolved {
        let mut r = request(Mode::LocalOnly, permissions);
        r.agent = Some(Agent::read(format!("---\nversion: 1\nname: reviewer\ndescription: d\ncapacity: specialized\npermissions: {ceiling}\ntools: {tools}\n---\nBody\r\n").as_bytes()).unwrap());
        r
    }

    #[test]
    fn named_role_is_the_primary_default_with_intersected_rules_everywhere() {
        let r = named(Permissions::Trusted, "read-only", "[search]");
        let doc = config(&r);
        let rules = ceiling(r.agent.as_ref().unwrap());
        assert_eq!(effective(&r), rules);
        assert_eq!(doc["permissions"], rules);
        assert_eq!(doc["default_agent"], "reviewer");
        assert_eq!(
            doc["agents"]["reviewer"],
            json!({"description": "d", "mode": "primary", "model": model(&r),
                   "permissions": rules, "system": "Body\r\n"})
        );
        assert_eq!(grantable(&r), ["search"]);
        // Deny invocation narrows every role; no kinds are grantable.
        let denied = named(Permissions::Deny, "trusted", "[read, edit, execute]");
        assert_eq!(effective(&denied), profile(Permissions::Deny));
        assert!(grantable(&denied).is_empty());
        assert!(grantable(&named(Permissions::Trusted, "deny", "[]")).is_empty());
        assert_eq!(
            grantable(&request(Mode::LocalOnly, Permissions::Trusted)),
            ["read", "search", "edit", "execute"]
        );
        let plain = config(&request(Mode::LocalOnly, Permissions::Trusted));
        assert_eq!(plain["default_agent"], "build");
        assert_eq!(plain["agents"].as_object().unwrap().len(), 1);
        // Only default effort is supported.
        let effort = |e: &str| {
            Agent::read(format!("---\nversion: 1\nname: x\ndescription: d\ncapacity: primary\npermissions: deny\ntools: []\neffort: {e}\n---\nb\n").as_bytes()).unwrap()
        };
        assert!(supports(&effort("default")).is_ok());
        for e in ["low", "medium", "high", "max"] {
            assert!(supports(&effort(e)).is_err(), "{e}");
        }
    }

    #[test]
    fn named_role_must_be_visible_primary_with_exact_model_and_system() {
        let r = named(Permissions::Trusted, "read-only", "[read]");
        let tail = json!({"action": "browser", "resource": "*", "effect": "deny"});
        let mut full = rules(&r, &[]);
        full.extend(effective(&r).as_array().unwrap().iter().cloned());
        full.push(tail);
        let wanted = json!({"id": "proxy", "providerID": "ah-litellm"});
        let mut role = agent("reviewer", full.clone(), wanted.clone());
        role["system"] = json!("Body\r\n");
        role["description"] = json!("d");
        let helper = agent("general", full.clone(), Value::Null);
        validate_agents(&r, &json!([helper, role])).unwrap();
        // `build` alone no longer satisfies a named request.
        assert!(validate_agents(&r, &json!([agent("build", full.clone(), Value::Null)])).is_err());
        let mut bad = Vec::new();
        for (field, value) in [
            ("mode", json!("subagent")),
            ("hidden", json!(true)),
            ("system", json!("Body")),
            ("description", json!("other")),
            ("model", Value::Null),
        ] {
            let mut changed = role.clone();
            changed[field] = value;
            bad.push(json!([changed]));
        }
        // A helper keeping the wider invocation profile fails.
        let mut wide = rules(&r, &[]);
        wide.extend(
            profile(Permissions::Trusted)
                .as_array()
                .unwrap()
                .iter()
                .cloned(),
        );
        bad.push(json!([role.clone(), agent("general", wide, Value::Null)]));
        for bad in bad {
            assert!(validate_agents(&r, &bad).is_err(), "{bad}");
        }
    }

    #[test]
    fn instructions_name_only_the_resolved_path_and_command_prompts_refuse() {
        let mut r = request(Mode::CloudOnly, Permissions::Deny);
        r.instructions = None;
        assert_eq!(config(&r)["instructions"], json!([]));
        r.instructions = Some("/p/AGENTS.md".into());
        assert_eq!(config(&r)["instructions"], json!(["/p/AGENTS.md"]));
        for prompt in ["/review", "  /init now", "\n/goal\tship", "/compact", "/x."] {
            assert!(prompt_supported(prompt).is_err(), "{prompt:?}");
        }
        for prompt in ["fix /init", "/src/main.rs fails", "/", "review", "a/b"] {
            assert!(prompt_supported(prompt).is_ok(), "{prompt:?}");
        }
    }

    #[test]
    fn catalog_must_contain_target_and_only_built_in_models() {
        let r = request(Mode::CloudOnly, Permissions::Deny);
        validate_catalog(&r, "opencode/a\nopencode/gpt-5.4\n").unwrap();
        assert!(validate_catalog(&r, "opencode/a\n").is_err());
        assert!(validate_catalog(&r, "opencode/gpt-5.4\nah-litellm/x\n").is_err());
    }
}
