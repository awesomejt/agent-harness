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
bin="$work/home/.local/bin"
/bin/mkdir -p "$bin" "$work/project" "$work/previous" \
    "$work/home/.config/opencode" "$work/home/.local/share/opencode"
# Upgrade: an earlier install, user/global runtime config and a login store must survive.
/usr/bin/printf '#!/bin/sh\necho "ah 0.0.0-previous"\n' > "$work/previous/ah"
/usr/bin/install -m 755 "$work/previous/ah" "$bin/ah"
/bin/echo '{"model":"user-global-sentinel"}' > "$work/home/.config/opencode/opencode.json"
/bin/echo '{"sentinel":"login-store"}' > "$work/home/.local/share/opencode/auth.json"
/bin/echo '{"$schema":"https://opencode.ai/config.json","theme":"user-sentinel"}' \
    > "$work/project/opencode.json"
/bin/cat > "$work/project/ah.json" <<'EOF'
{"version":1,"mode":"local-only","model":"smoke-alias","litellm":{"api_base":"http://127.0.0.1:9/v1","api_key_env":"SMOKE_KEY"}}
EOF
snapshot() {
    (cd "$work" && /usr/bin/find home project -path home/.local/bin -prune -o -type f -print \
        | /usr/bin/sort | /usr/bin/xargs /usr/bin/shasum -a 256)
}
snapshot > "$work/before"
/usr/bin/tar -xzf "$assets/$name.tar.gz" -C "$work"
/usr/bin/install -m 755 "$work/$name/ah" "$bin/ah"
/usr/bin/codesign --verify "$bin/ah"
/bin/test -f "$work/$name/third-party/inventory.json"
/bin/test -f "$work/$name/third-party/rust-1.88.0/COPYRIGHT-library.html"
for file in INSTALL.md BUILD-INFO.json examples/ah.local-only.json examples/ah.cloud-only.json \
    examples/ah.local-first.json examples/agents/coder.md examples/agents/reviewer.md; do
    /bin/test -f "$work/$name/$file"
done
run() {
    /usr/bin/env -i HOME="$work/home" PATH="$bin" SMOKE_KEY=smoke-secret \
        LITELLM_API_KEY=litellm-secret OPENCODE_API_KEY=native-secret ah "$@"
}
/bin/test "$(run --version)" = "ah $version"
run --help > "$work/help"
/usr/bin/grep -q 'single' "$work/help"
/usr/bin/grep -q -- '--agent' "$work/help"
run single 'smoke-prompt' --project "$work/project" --preview > "$work/preview" 2> "$work/preview.err"
/usr/bin/grep -q 'missing; install OpenCode 2.2.5' "$work/preview"
/usr/bin/grep -q 'execution platform: macOS (supported)' "$work/preview"
/usr/bin/grep -q 'health checks: none' "$work/preview"
if /usr/bin/grep -E 'smoke-secret|smoke-prompt|127.0.0.1' "$work/preview" "$work/preview.err"; then
    exit 1
fi
expect() {
    want=$1
    shift
    set +e
    "$@" > "$work/out" 2> "$work/err"
    code=$?
    set -e
    /bin/test "$code" = "$want"
}
expect 2 run single 'smoke' --project "$work/project" --mode cloud-only
expect 2 run single 'smoke' --project "$work/project" --preview --output jsonl
expect 2 /usr/bin/env -i HOME="$work/home" PATH="$bin" \
    ah single smoke --project "$work/project" --preview
# Every packaged sample config previews with both packaged agents and writes nothing.
for mode in local-only cloud-only local-first; do
    sample="$work/sample-$mode"
    /bin/mkdir -p "$sample/agents"
    /bin/cp "$work/$name/examples/ah.$mode.json" "$sample/ah.json"
    /bin/cp "$work/$name/examples/agents/"*.md "$sample/agents/"
    for agent in coder reviewer; do
        run single 'sample-prompt' --project "$sample" --agent "$agent" --preview \
            > "$work/out" 2> "$work/err"
        /usr/bin/grep -q "^mode: $mode (config)" "$work/out"
        /usr/bin/grep -q "^agent: \"$agent\"" "$work/out"
        if /usr/bin/grep -E 'secret|sample-prompt|your-proxy' "$work/out" "$work/err"; then
            exit 1
        fi
    done
    /bin/test "$(/usr/bin/find "$sample" -type f | /usr/bin/wc -l | /usr/bin/tr -d ' ')" = 3
done
snapshot > "$work/after"
/usr/bin/cmp -s "$work/before" "$work/after"
# Rollback restores the retained earlier executable; reinstalling restores this one.
/usr/bin/install -m 755 "$work/previous/ah" "$bin/ah"
/bin/test "$(run --version)" = "ah 0.0.0-previous"
/usr/bin/install -m 755 "$work/$name/ah" "$bin/ah"
/bin/test "$(run --version)" = "ah $version"
/bin/echo "Archive upgrade/rollback, version/help, sample previews, redaction, preservation and rejection smoke passed (no toolchains on PATH)."
