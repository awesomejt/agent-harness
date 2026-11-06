#!/usr/bin/env python3
"""Checks relative links in the Markdown documentation under ROOT.

Usage: python3 scripts/tests/doclinks.py [ROOT]. ROOT defaults to this
repository's root, derived from this script's location rather than the working
directory; a ROOT that is not an existing directory exits 2.

Files checked are the `*.md` files tracked by Git under ROOT (`git ls-files`).
Links checked are inline links and images, `[text](target)` and `![alt](target)`,
with an optional quoted title. Targets with a URL scheme (`https:`, `mailto:`,
and so on) are skipped, as is anything inside a fenced code block or an inline
code span. A target's path is resolved relative to the linking file and must
exist as a file or a directory, following symlinks; an absolute path is reported
as broken. A `#fragment`, alone (the same file) or after a
`.md` path, must match an anchor in that Markdown file: an explicit
`<a id="...">` or a heading's GitHub slug (lowercase; punctuation dropped except
hyphens and underscores; each space becomes a hyphen; repeated headings take
`-1`, `-2`, ... suffixes). Fragments are case-sensitive.

Each broken link is one line on stdout: `PATH:LINE: TARGET`, PATH relative to
ROOT and LINE 1-based. Exit 0 when no link is broken, 1 when one is, and 2 for a
bad ROOT or a failed `git ls-files`.
"""
import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

# A fenced code block opener: up to three spaces then three or more of one
# character, plus that fence's info string.
FENCE = re.compile(r'^ {0,3}(`{3,}|~{3,})(.*)$')
# ATX heading, with its optional closing sequence kept for stripping.
HEADING = re.compile(r'^ {0,3}#{1,6}(?:[ \t]+(.*))?$')
# An explicit HTML anchor, as used by tasks/*.md.
ANCHOR_TAG = re.compile(r'''<a\b[^>]*?\bid=(?:"([^"]*)"|'([^']*)')''')
# A scheme as in RFC 3986: https:, mailto:, irc:, data:, ...
SCHEME = re.compile(r'^[A-Za-z][A-Za-z0-9+.\-]*:')
# Inline link/image syntax inside heading text, unwrapped before slugging.
HEADING_LINK = re.compile(r'!?\[([^\[\]]*)\](?:\([^()]*\)|\[[^\[\]]*\]|\[\])')
# A destination: no plain whitespace, but `\X` (including `\ `) counts as content.
DEST = re.compile(r'(?:\\[^\n]|[^\s\\])*')
# Only ASCII punctuation and space lose their backslash, as CommonMark does.
ESCAPED = re.compile(r'\\([' + re.escape(r'''!"#$%&'()*+,-./:;<=>?@[\]^_`{|}~ ''') + r'])')


def run_git(root):
    """`git ls-files -z` for root, or None when Git fails."""
    completed = subprocess.run(['git', '-C', str(root), 'ls-files', '-z'],
                               capture_output=True)
    if completed.returncode != 0:
        sys.stderr.write(completed.stderr.decode('utf-8', 'replace'))
        print('error: git ls-files failed on %s' % root, file=sys.stderr)
        return None
    return completed.stdout.decode('utf-8', 'surrogateescape')


def tracked_markdown(root):
    """Tracked `*.md` paths under root, relative to root and sorted."""
    listing = run_git(root)
    if listing is None:
        return None
    names = [name for name in listing.split('\0') if name.endswith('.md')]
    return sorted(name for name in names if (root / name).is_file())


def fenced_flags(lines):
    """Mark every line inside a fenced code block, including the fences."""
    flags = [False] * len(lines)
    fence = None
    for index, line in enumerate(lines):
        match = FENCE.match(line)
        if fence is None:
            if match and (match.group(1)[0] == '~' or '`' not in match.group(2)):
                fence = (match.group(1)[0], len(match.group(1)))
                flags[index] = True
            continue
        body = line.strip()
        closes = (bool(body) and body[0] == fence[0] and len(body) >= fence[1]
                  and set(body) == {fence[0]} and len(line) - len(line.lstrip(' ')) <= 3)
        flags[index] = True
        if closes:
            fence = None
    return flags


def mask_code_spans(text):
    """Replace inline code spans and their delimiters with spaces."""
    out = list(text)
    index = 0
    while index < len(text):
        if text[index] != '`':
            index += 1
            continue
        run_end = index
        while run_end < len(text) and text[run_end] == '`':
            run_end += 1
        run = run_end - index
        close = closing_run(text, run_end, run)
        if close is None:
            index = run_end
            continue
        for position in range(index, close + run):
            if out[position] != '\n':
                out[position] = ' '
        index = close + run
    return ''.join(out)


def closing_run(text, start, run):
    """Index of the next backtick run of exactly `run` backticks, or None."""
    index = start
    while index < len(text):
        if text[index] != '`':
            index += 1
            continue
        end = index
        while end < len(text) and text[end] == '`':
            end += 1
        if end - index == run:
            return index
        index = end
    return None


def masked_text(text):
    """The file text with code blocks and code spans blanked to same-length spaces."""
    lines = text.split('\n')
    flags = fenced_flags(lines)
    masked = ['' if flag else line for flag, line in zip(flags, lines)]
    segments = []
    index = 0
    while index < len(masked):
        if masked[index] == '':
            index += 1
            continue
        end = index
        while end < len(masked) and masked[end] != '':
            end += 1
        segments.append((index, end))
        index = end
    for start, end in segments:
        span = mask_code_spans('\n'.join(masked[start:end]))
        masked[start:end] = span.split('\n')
    # Blank fenced lines only now, so a code span cannot pair across a fence.
    masked = [' ' * len(line) if flag else piece
              for flag, line, piece in zip(flags, lines, masked)]
    joined = '\n'.join(masked)
    assert len(joined) == len(text), 'masking must preserve offsets'
    return joined, flags


def line_of(text, offset):
    """1-based line holding offset."""
    return text.count('\n', 0, offset) + 1


def match_bracket(text, start):
    """Index of the `]` matching the `[` at start, or None."""
    depth = 0
    index = start
    while index < len(text):
        char = text[index]
        if char == '\\':
            index += 2
            continue
        if char in '[]':
            depth += 1 if char == '[' else -1
            if depth == 0:
                return index
        index += 1
    return None


def match_paren(text, start):
    """Index of the `)` matching the `(` at start, or None; angle parts are opaque."""
    depth = 0
    angle = False
    index = start
    while index < len(text):
        char = text[index]
        if char == '\\':
            index += 2
            continue
        if char == '\n':
            return None
        if char == '<':
            angle = True
        elif char == '>':
            angle = False
        elif not angle:
            if char == '(':
                depth += 1
            elif char == ')':
                depth -= 1
                if depth == 0:
                    return index
        index += 1
    return None


def destination(raw):
    """The target of an inline link: its optional `<...>` body, up to any title."""
    raw = raw.strip()
    if raw.startswith('<'):
        end = raw.find('>')
        return raw[1:end] if end != -1 else raw[1:].strip()
    # A bare destination ends at the first unescaped whitespace, before any title.
    found = DEST.match(raw)
    if not found:
        return ''
    return ESCAPED.sub(r'\1', found.group())


def find_links(text):
    """Yield (offset, target) for every inline link and image in masked text."""
    index = 0
    while index < len(text):
        if text[index] != '[' or (index and text[index - 1] == '\\'):
            index += 1
            continue
        close = match_bracket(text, index)
        if close is None:
            index += 1
            continue
        if close + 1 < len(text) and text[close + 1] == '(':
            end = match_paren(text, close + 1)
            if end is not None:
                yield index, destination(text[close + 2:end])
                index = end + 1
                continue
        index = close + 1


def heading_slug(text):
    """GitHub's slug for a heading's text."""
    text = HEADING_LINK.sub(lambda match: match.group(1), text or '')
    text = re.sub(r'[ \t]+#+[ \t]*$', '', text).strip()
    text = re.sub(r'[^\w\s-]', '', text, flags=re.UNICODE)
    return re.sub(r'\s', '-', text).lower()


def anchors(text, flags):
    """Anchors of a Markdown file: explicit `<a id=...>` plus heading slugs."""
    found = set()
    seen = {}
    lines = text.split('\n')
    for index, line in enumerate(lines):
        if flags[index]:
            continue
        for match in ANCHOR_TAG.finditer(line):
            value = match.group(1) or match.group(2)
            if value:
                found.add(value)
        heading = HEADING.match(line)
        if not heading:
            continue
        slug = heading_slug(heading.group(1))
        if not slug:
            continue
        count = seen.get(slug, 0)
        seen[slug] = count + 1
        found.add('%s-%d' % (slug, count) if count else slug)
    return found


def resolves(origin, target, cache):
    """True when the target's path exists and any fragment matches an anchor."""
    path, _, fragment = target.partition('#')
    # An absolute path would be checked against the host, not ROOT, so it is broken.
    if os.path.isabs(path):
        return False
    resolved = Path(os.path.normpath(origin if not path else origin.parent / path))
    # exists() follows symlinks, so a dangling link fails like a missing file.
    if not resolved.exists():
        return False
    if not fragment:
        return True
    # A fragment is only an anchor promise for the same file or for another .md.
    if resolved != origin and resolved.suffix != '.md':
        return True
    if not resolved.is_file():
        return False
    if resolved not in cache:
        text = resolved.read_text(encoding='utf-8', errors='replace')
        cache[resolved] = anchors(text, fenced_flags(text.split('\n')))
    return fragment in cache[resolved]


def main(argv=None):
    parser = argparse.ArgumentParser(prog='doclinks.py', usage='%(prog)s [ROOT]',
                                     description='Check relative links in Markdown documents.')
    parser.add_argument('root', nargs='?', metavar='ROOT',
                        help='directory to check; defaults to this repository root')
    args = parser.parse_args(argv)
    root = Path(args.root) if args.root else Path(__file__).resolve().parents[2]
    if not root.is_dir():
        print('error: %s is not a directory' % root, file=sys.stderr)
        return 2
    root = root.resolve()
    files = tracked_markdown(root)
    if files is None:
        return 2

    broken = 0
    cache = {}
    for name in files:
        origin = root / name
        text = origin.read_text(encoding='utf-8', errors='replace')
        masked, _ = masked_text(text)
        for offset, target in find_links(masked):
            if not target or SCHEME.match(target):
                continue
            if not resolves(origin, target, cache):
                print('%s:%d: %s' % (name, line_of(text, offset), target))
                broken += 1
    return 1 if broken else 0


if __name__ == '__main__':
    sys.exit(main())
