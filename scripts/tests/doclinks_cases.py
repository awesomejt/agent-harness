#!/usr/bin/env python3
"""Fixture cases for scripts/tests/doclinks.py (P6.4 work product, P6.5 R06-08).

Each case builds a temporary Git repository with tracked Markdown, runs the
checker on it and compares the exit and the reported `PATH:LINE: TARGET`
lines. No `ah`, runtime or network.
"""
from pathlib import Path
import subprocess
import sys
import tempfile

CHECKER = Path(__file__).resolve().parent / 'doclinks.py'


def check(files, expect, broken=()):
    with tempfile.TemporaryDirectory(prefix='ah-doclinks-') as d:
        root = Path(d)
        subprocess.run(['git', 'init', '-q', str(root)], check=True)
        for name, text in files.items():
            (root / name).parent.mkdir(parents=True, exist_ok=True)
            (root / name).write_text(text)
        subprocess.run(['git', '-C', str(root), 'add', '.'], check=True)
        done = subprocess.run([sys.executable, '-I', str(CHECKER), str(root)],
                              capture_output=True, text=True, timeout=60)
        assert done.returncode == expect, (files, done.returncode, done.stdout, done.stderr)
        assert done.stdout.splitlines() == list(broken), (files, done.stdout)
        print('PASS', next(iter(files.values())).splitlines()[0][:60], expect, flush=True)


# R06-08: an HTML anchor written only as an inline-code example is no anchor.
check({'README.md': 'Example: `<a id="ghost"></a>`.\n\n[Broken link](#ghost)\n'}, 1, ['README.md:3: #ghost'])
# ... nor inside a fenced block, in this file or a linked one.
check({'README.md': '```html\n<a id="ghost"></a>\n```\n\n[Broken](#ghost) [Other](other.md#ghost)\n',
       'other.md': 'Example: ``<a id="ghost"></a>``\n'},
      1, ['README.md:5: #ghost', 'README.md:5: other.md#ghost'])
# A real HTML anchor resolves, in this file and from another file.
check({'README.md': '<a id="real"></a>\nText.\n\n[Here](#real) [There](docs/a.md#card-1)\n',
       'docs/a.md': "<a id='card-1'></a>\n# Cards\n"}, 0)
# A heading containing inline code keeps that code's text in its slug, and an
# anchor-like code span in the heading adds no explicit anchor.
check({'README.md': '# The `ah ralph` command\n\n## Use `<a id="fake">`\n\n'
                    '[Command](#the-ah-ralph-command) [Use](#use-a-idfake)\n'}, 0)
check({'README.md': '## Use `<a id="fake">`\n\n[Fake](#fake)\n'}, 1, ['README.md:3: #fake'])
# Repeated headings take numeric suffixes; fragments are case-sensitive.
check({'README.md': '# Step\n# Step\n\n[Second](#step-1) [Case](#Step)\n'}, 1, ['README.md:4: #Step'])
# Paths: missing and absolute targets are broken; code spans and schemes skipped.
check({'README.md': '[Missing](absent.md) [Abs](/etc/hosts) `[Code](absent.md)` [Web](https://example.com/x)\n'},
      1, ['README.md:1: absent.md', 'README.md:1: /etc/hosts'])

print('doclinks_cases: all cases passed')
