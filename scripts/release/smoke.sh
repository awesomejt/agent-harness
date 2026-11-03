#!/bin/sh
# Install/test an actual archive with only ah on PATH. No Rust/Python/runtime/service.
set -eu
assets=$1
version=$2
assets=$(cd "$assets" && pwd)
name="ah-v${version}-aarch64-apple-darwin"
(cd "$assets" && /usr/bin/shasum -a 256 -c SHA256SUMS)
work=$(/usr/bin/mktemp -d "${TMPDIR:-/tmp}/ah-install.XXXXXX")
trap '/bin/rm -rf "$work"' EXIT HUP INT TERM
/bin/mkdir -p "$work/home/.local/bin" "$work/project"
/usr/bin/tar -xzf "$assets/$name.tar.gz" -C "$work"
/usr/bin/install -m 755 "$work/$name/ah" "$work/home/.local/bin/ah"
/usr/bin/codesign --verify "$work/home/.local/bin/ah"
/bin/test -f "$work/$name/third-party/inventory.json"
/bin/test -f "$work/$name/third-party/rust-1.88.0/COPYRIGHT-library.html"
/bin/cat > "$work/project/ah.json" <<'EOF'
{"version":1,"mode":"local-only","model":"smoke-alias","litellm":{"api_base":"http://127.0.0.1:9/v1","api_key_env":"SMOKE_KEY"}}
EOF
run() {
    /usr/bin/env -i HOME="$work/home" PATH="$work/home/.local/bin" SMOKE_KEY=smoke-secret \
        ah "$@"
}
/bin/test "$(run --version)" = "ah $version"
run --help > "$work/help"
/usr/bin/grep -q 'single' "$work/help"
run single 'smoke-prompt' --project "$work/project" --preview > "$work/preview" 2> "$work/preview.err"
/usr/bin/grep -q 'missing; install OpenCode [0-9]' "$work/preview"
/usr/bin/grep -q 'health checks: none' "$work/preview"
if /usr/bin/grep -E 'smoke-secret|smoke-prompt|127.0.0.1' "$work/preview" "$work/preview.err"; then
    exit 1
fi
/bin/test ! -e "$work/project/opencode.json"
/bin/test ! -e "$work/project/.ah-opencode-owner.json"
set +e
run single 'smoke' --project "$work/project" --mode cloud-only > "$work/out" 2> "$work/err"
code=$?
set -e
/bin/test "$code" = 2
set +e
/usr/bin/env -i HOME="$work/home" PATH="$work/home/.local/bin" \
    ah single smoke --project "$work/project" --preview > "$work/out" 2> "$work/err"
code=$?
set -e
/bin/test "$code" = 2
/bin/test "$(/usr/bin/find "$work/project" -type f | /usr/bin/wc -l | /usr/bin/tr -d ' ')" = 1
/bin/echo "Archive installation, version/help, preview, redaction and rejection smoke passed (no toolchains on PATH)."
