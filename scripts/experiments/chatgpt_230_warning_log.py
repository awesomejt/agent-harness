#!/usr/bin/env python3
"""Strict, sanitized parser for the disposable 2.3.0 warning diagnostic."""
import datetime as dt
import json
import os
from pathlib import Path
import re
import stat
import math

from antigravity_feasibility import LIMIT

MAX_LINE = 64 * 1024
MAX_RECORDS = 10_000
RUN = re.compile(r"^[0-9a-f]{8}$")
KEY = re.compile(r"[A-Za-z_][A-Za-z0-9_.]*")


class Refusal(RuntimeError):
    """A static code only; callers must not render the rejected input."""


# Each accepted tuple was checked against the D095 pinned public source.
MESSAGES = {
    ("ERROR", "failed to watch directory"): ("WATCH_START", "path"),
    ("ERROR", "watcher callback failed"): ("WATCH_CALLBACK", None),
    ("ERROR", "watcher backend not supported"): ("WATCH_BACKEND", "directory"),
    ("ERROR", "failed to subscribe"): ("WATCH_SUBSCRIBE", "directory"),
    ("WARN", "configuration normalization diagnostic"): ("CONFIG_NORMALIZATION", "source"),
    ("ERROR", "failed to reload config"): ("CONFIG_RELOAD", None),
    ("ERROR", "failed to reload wellknown config"): ("CONFIG_RELOAD", None),
    ("ERROR", "failed to reload wellknown sources"): ("CONFIG_RELOAD", None),
    ("WARN", "failed to refresh wellknown manifests"): ("CONFIG_RELOAD", None),
    ("WARN", "failed to refresh wellknown config"): ("CONFIG_RELOAD", None),
    ("WARN", "failed to load wellknown config"): ("CONFIG_RELOAD", None),
    ("WARN", "failed to discover wellknown config"): ("CONFIG_RELOAD", None),
    ("WARN", "failed to convert managed preferences"): ("CONFIG_RELOAD", "source"),
    ("WARN", "config file reference is missing or unreadable"): ("RESOURCE_INPUT", "path"),
    ("WARN", "agent file skipped"): ("RESOURCE_INPUT", "filepath"),
    ("WARN", "ignored unsupported agent fields"): ("RESOURCE_INPUT", "path"),
    ("WARN", "command file skipped"): ("RESOURCE_INPUT", "filepath"),
    ("WARN", "failed to load skill source"): ("RESOURCE_INPUT", None),
    ("WARN", "failed to fetch instruction url"): ("RESOURCE_INPUT", None),
    ("WARN", "failed to load instruction source"): ("RESOURCE_INPUT", None),
    ("WARN", "failed to activate instruction source"): ("RESOURCE_INPUT", None),
    ("ERROR", "configured plugin watch failed"): ("PLUGIN_INPUT", "target"),
    ("WARN", "configured plugin path must be a directory"): ("PLUGIN_INPUT", "target"),
    ("ERROR", "failed to reload MCP config"): ("PLUGIN_INPUT", None),
    ("ERROR", "uncaught exception"): ("CLI_FAILURE", None),
    ("ERROR", "unhandled rejection"): ("CLI_FAILURE", None),
    ("ERROR", "cli process failed"): ("CLI_FAILURE", None),
    ("WARN", "Ignoring invalid PTY restart handoff; persistent terminals will start fresh"): ("OTHER_SOURCE_WARNING", None),
    ("WARN", "failed to change service directory to home"): ("OTHER_SOURCE_WARNING", None),
}


def _value(line, cursor):
    if cursor >= len(line):
        raise Refusal("log-malformed")
    if line[cursor] in '"[{':
        try:
            value, used = json.JSONDecoder().raw_decode(line[cursor:])
        except (ValueError, TypeError):
            raise Refusal("log-malformed") from None
        end = cursor + used
        if end < len(line) and line[end] != " ":
            raise Refusal("log-malformed")
        return value, end
    end = cursor
    while end < len(line) and line[end] != " ":
        if line[end] in '"=':
            raise Refusal("log-malformed")
        end += 1
    if end == cursor:
        raise Refusal("log-malformed")
    return line[cursor:end], end


def parse(raw):
    """Parse fully formatted logger lines without retaining their raw text."""
    if not isinstance(raw, bytes) or len(raw) > LIMIT:
        raise Refusal("log-bounds")
    try:
        text = raw.decode("utf-8", "strict")
    except UnicodeDecodeError:
        raise Refusal("log-encoding") from None
    if not text or not text.endswith("\n"):
        raise Refusal("log-truncated")
    if "\r" in text or "\t" in text or any(ord(char) < 32 and char != "\n" for char in text):
        raise Refusal("log-malformed")
    lines = text[:-1].split("\n")
    if len(lines) > MAX_RECORDS or any(not line or len(line.encode()) > MAX_LINE for line in lines):
        raise Refusal("log-bounds")
    records = []
    for line in lines:
        cursor, fields = 0, {}
        while cursor < len(line):
            match = KEY.match(line, cursor)
            if not match or match.end() >= len(line) or line[match.end()] != "=":
                raise Refusal("log-malformed")
            key = match.group()
            if key in fields:
                raise Refusal("log-duplicate")
            value, cursor = _value(line, match.end() + 1)
            fields[key] = value
            if cursor == len(line):
                break
            if line[cursor] != " ":
                raise Refusal("log-malformed")
            cursor += 1
            if cursor == len(line):
                raise Refusal("log-malformed")
        records.append(fields)
    return records


def read_log(path, work):
    """Read one newly-owned regular log below work without following links."""
    path, work = Path(path), Path(work)
    if not path.is_absolute() or not work.is_absolute():
        raise Refusal("log-path")
    try:
        resolved_work = work.resolve(strict=True)
        relative = path.relative_to(resolved_work)
    except (OSError, ValueError):
        raise Refusal("log-path") from None
    if not relative.parts or any(part in {"", ".", ".."} for part in relative.parts):
        raise Refusal("log-path")
    directory_flags = os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_NOFOLLOW", 0)
    try:
        directory = os.open(resolved_work, directory_flags)
    except OSError:
        raise Refusal("log-open") from None
    flags = os.O_RDONLY | os.O_NONBLOCK | getattr(os, "O_NOFOLLOW", 0)
    try:
        for part in relative.parts[:-1]:
            child = os.open(part, directory_flags, dir_fd=directory)
            os.close(directory)
            directory = child
        fd = os.open(relative.parts[-1], flags, dir_fd=directory)
    except OSError:
        os.close(directory)
        raise Refusal("log-open") from None
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_uid != os.getuid():
            raise Refusal("log-identity")
        if before.st_size > LIMIT:
            raise Refusal("log-bounds")
        chunks, remaining = [], before.st_size
        while remaining:
            chunk = os.read(fd, min(remaining, 64 * 1024))
            if not chunk:
                raise Refusal("log-race")
            chunks.append(chunk)
            remaining -= len(chunk)
        data = b"".join(chunks)
        after = os.fstat(fd)
        named = os.stat(relative.parts[-1], dir_fd=directory, follow_symlinks=False)
        if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns):
            raise Refusal("log-race")
        if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (named.st_dev, named.st_ino, named.st_size, named.st_mtime_ns, named.st_ctime_ns):
            raise Refusal("log-race")
        return data
    finally:
        os.close(fd)
        os.close(directory)


def _timestamp(value):
    if not isinstance(value, str) or not value.endswith("Z"):
        raise Refusal("log-timestamp")
    try:
        result = dt.datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
    except (ValueError, AttributeError):
        raise Refusal("log-timestamp") from None
    if not math.isfinite(result):
        raise Refusal("log-timestamp")
    return result


def _args(value):
    if not isinstance(value, str):
        raise Refusal("log-startup")
    try:
        value = json.loads(value)
    except ValueError:
        raise Refusal("log-startup") from None
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise Refusal("log-startup")
    return value


def verify_messages(packages):
    """Recheck this finite table against the D095 hash-pinned source manifest."""
    root = Path(packages)
    manifest_path = Path(__file__).resolve().parents[2] / "docs/evidence/p7-9-230-warning-source-manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text())
    except (OSError, ValueError):
        raise Refusal("warning-manifest") from None
    files = manifest.get("files")
    if not isinstance(files, dict) or not files:
        raise Refusal("warning-manifest")
    import hashlib
    source = {}
    for relative, expected_hash in files.items():
        path = root / relative
        try:
            data = path.read_bytes()
        except OSError:
            raise Refusal("warning-manifest") from None
        if hashlib.sha256(data).hexdigest() != expected_hash:
            raise Refusal("warning-manifest")
        source[relative] = data.decode("utf-8", "strict")
    literals = set()
    for text in source.values():
        for match in re.finditer(r'Effect\.log(Warning|Error)\(\s*"([^"\n]+)"', text):
            literals.add(("WARN" if match.group(1) == "Warning" else "ERROR", match.group(2)))
    if not set(MESSAGES) <= literals:
        raise Refusal("warning-source")
    return {"files": len(files), "messages": len(MESSAGES)}


def _string(fields, key, code):
    value = fields.get(key)
    if not isinstance(value, str):
        raise Refusal(code)
    return value


def classify(raw, expected, targets, *, windows=None, version="2.3.0", channel="latest"):
    """Return a sanitized summary; a non-empty warnings list remains a refusal to callers."""
    if set(expected) != {"SERVER", "DEBUG_CONFIG", "DEBUG_AGENTS"}:
        raise Refusal("log-expectation")
    if not all(isinstance(args, list) and all(isinstance(arg, str) for arg in args) for args in expected.values()):
        raise Refusal("log-expectation")
    labels = {"PARENT_REPO", "OTHER_OWNED", "PROJECT", "GLOBAL_CONFIG"}
    if not all(isinstance(key, str) and isinstance(value, str) and value in labels for key, value in targets.items()):
        raise Refusal("log-targets")
    if windows is None or set(windows) != set(expected):
        raise Refusal("log-windows")
    records = parse(raw)
    starters, labels, roles = {}, {}, {label: set() for label in expected}
    expected_tuples = {tuple(args): label for label, args in expected.items()}
    if len(expected_tuples) != len(expected):
        raise Refusal("log-expectation")
    for fields in records:
        if not {"timestamp", "level", "run", "message"} <= set(fields):
            raise Refusal("log-malformed")
        if _string(fields, "message", "log-malformed") != "cli starting":
            continue
        if (_string(fields, "level", "log-malformed") != "INFO" or
                _string(fields, "version", "log-startup") != version or
                _string(fields, "channel", "log-startup") != channel):
            raise Refusal("log-startup")
        run = _string(fields, "run", "log-startup")
        args = tuple(_args(fields.get("args")))
        label = expected_tuples.get(args)
        if not RUN.fullmatch(run) or label is None or run in labels or label in starters:
            raise Refusal("log-startup")
        starters[label], labels[run] = fields, label
    if set(starters) != set(expected):
        raise Refusal("log-startup")
    for fields in records:
        run = _string(fields, "run", "log-malformed")
        label = labels.get(run)
        if label is None:
            raise Refusal("log-provenance")
        period = windows[label]
        if not (isinstance(period, tuple) and len(period) == 2 and all(isinstance(value, (int, float)) and math.isfinite(value) for value in period) and period[0] <= period[1]):
            raise Refusal("log-windows")
        stamp = _timestamp(fields.get("timestamp", ""))
        if not period[0] <= stamp <= period[1]:
            raise Refusal("log-window")
        role = fields.get("role")
        if role is not None:
            if not isinstance(role, str):
                raise Refusal("log-role")
            if role not in {"cli", "server"}:
                raise Refusal("log-role")
            roles[label].add(role)
    if roles["SERVER"] != {"cli", "server"} or any(roles[label] != {"cli"} for label in ("DEBUG_CONFIG", "DEBUG_AGENTS")):
        raise Refusal("log-role")
    warnings = {}
    for fields in records:
        level = _string(fields, "level", "log-malformed")
        if level not in {"INFO", "DEBUG", "WARN", "ERROR"}:
            raise Refusal("log-level")
        if level not in {"WARN", "ERROR"}:
            continue
        message = _string(fields, "message", "log-malformed")
        family = MESSAGES.get((level, message))
        if family is None:
            raise Refusal("unknown-warning")
        family, field = family
        target = "NONE"
        if field is not None:
            value = _string(fields, field, "warning-target")
            target = ("NONE" if message == "configuration normalization diagnostic" and
                      value == "OPENCODE_CONFIG_CONTENT" else targets.get(value))
            if target is None:
                raise Refusal("warning-target")
        # Parcel watcher callbacks have no path, unlike the node callback.
        # When the latter supplies one it must remain within the owned map.
        if message == "watcher callback failed" and "path" in fields:
            target = targets.get(_string(fields, "path", "warning-target"))
            if target is None:
                raise Refusal("warning-target")
        key = (labels[fields["run"]], family, target)
        warnings[key] = warnings.get(key, 0) + 1
    output = [{"process": process, "family": family, "target": target, "count": count}
              for (process, family, target), count in sorted(warnings.items())]
    return {"processes": len(labels), "records": len(records), "warnings": output}
