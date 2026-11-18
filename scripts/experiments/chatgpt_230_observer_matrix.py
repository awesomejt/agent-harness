#!/usr/bin/env python3
"""D102 opt-in rerun of the D094 matrix without retired case 3; setup review MUST precede installed use.

Reuses the merged D094 helper unchanged: same source audit, executable pin,
transport/containment controls, per-case run_case and child environment. The
only differences are which rows run and that output labels keep D094 numbering.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile

import chatgpt_230_observer as d094
from chatgpt_230_observer import Refusal, require

# Copied verbatim from chatgpt_230_observer.main; an offline case asserts equality
# with the merged literal so the rows cannot drift silently.
# (project_on, claude_on, reload, ancestor_denied, listing_denied)
D094_MATRIX = ((False, False, True, True, False), (True, False, False, True, False),
               (True, False, False, True, True), (False, True, False, True, False),
               (True, True, True, True, False), (True, False, True, False, False))
RETIRED = frozenset({3})  # D101: listing-denied parent; gates unsatisfiable as designed
ROWS = tuple((number, row) for number, row in enumerate(D094_MATRIX, 1) if number not in RETIRED)


def run_matrix(executable, builtin):
    """Run every retained row in D094 order; the first refusal stops the run."""
    cases = []
    for number, row in ROWS:
        print('START: disposable resource/inventory case ' + str(number), flush=True)
        cases.append(dict(d094.run_case(executable, builtin, *row), case=number))
        print('PASS: disposable resource/inventory case ' + str(number), flush=True)
    return cases


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True, help='clean official v2.3.0 checkout')
    parser.add_argument('--opencode', default='opencode')
    args = parser.parse_args()
    d094.check(sys.platform == 'darwin' and Path(d094.old.PYTHON).is_file())
    source = d094.audit(args.source)
    builtin = frozenset(source['plugins']['ids'])
    installed = shutil.which(args.opencode)
    d094.check(installed is not None)
    with tempfile.TemporaryDirectory(prefix='ah-230-binary-') as directory:
        executable = Path(directory).resolve() / 'opencode-cli'
        shutil.copy2(installed, executable)
        require(hashlib.sha256(executable.read_bytes()).hexdigest() == d094.SHA256, 'executable-pin')
        print('START: pinned disposable transport/containment controls', flush=True)
        d094.transport_controls(executable)
        cases = run_matrix(executable, builtin)
    print(json.dumps({'source_commit': source['source_commit'], 'executable_sha256': d094.SHA256,
                      'retired': sorted(RETIRED), 'cases': cases}, sort_keys=True))
    print('LIMIT: disposable no-auth qualification without case 3; catalog/retained/authenticated gates remain open')


if __name__ == '__main__':
    try:
        main()
    except Refusal as error:
        print('REFUSED: ' + str(error), file=sys.stderr)
        sys.exit(1)
    except Exception:
        print('REFUSED: control-gate; raw diagnostics withheld', file=sys.stderr)
        sys.exit(1)
