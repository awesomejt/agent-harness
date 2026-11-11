#!/usr/bin/env python3
"""Runs the offline suites: every current check that never contacts a live model provider.

Entries come from the "Rust and release checks" block of docs/TESTING.md in the
order they appear there, including each single_runtime.py variant with its flag,
then the sequence, named-role execution and inherited-capability suites that the
block omits. roles_live.py and claude_live.py are excluded because they contact live
providers, and scripts/experiments/ is excluded because it is historical
regression tooling. Each entry is the argument list after python3; every entry
runs with the repository root as the working directory. Written by the P5.4
live sequence use gate (docs/evidence/p5-4-sequence-use-gate.md).
"""
import argparse
import os
import subprocess
import sys
import time

SUITES = [
    ['scripts/tests/single.py'],
    ['scripts/tests/preview.py'],
    ['scripts/tests/worktree.py'],
    ['scripts/tests/single_runtime.py'],
    ['scripts/tests/single_runtime.py', '--cancel'],
    ['scripts/tests/single_runtime.py', '--group=coder'],
    ['scripts/tests/single_runtime.py', '--refuse'],
    ['scripts/tests/native.py'],
    ['scripts/tests/native_runtime.py'],
    ['scripts/tests/claude.py'],
    ['scripts/tests/codex_feasibility_cases.py'],
    ['scripts/tests/grok_feasibility_cases.py'],
    ['scripts/tests/antigravity_feasibility_cases.py'],
    ['scripts/tests/pi_feasibility_cases.py'],
    ['scripts/tests/pi_resource_route_cases.py'],
    ['scripts/tests/chatgpt_contained_cases.py'],
    ['scripts/tests/chatgpt_observer_cases.py'],
    ['scripts/tests/chatgpt_retained_cases.py'],
    ['scripts/tests/agents_runtime.py'],
    ['scripts/tests/agent_emission_runtime.py'],
    ['scripts/tests/local_first.py'],
    ['scripts/tests/modes.py'],
    ['scripts/tests/agents_exec.py'],
    ['scripts/tests/machine.py'],
    ['scripts/tests/verify.py'],
    ['scripts/tests/single_runtime.py', '--verify'],
    ['scripts/tests/sequence.py'],
    ['scripts/tests/sequence_state.py'],
    ['scripts/tests/sequence_runtime.py'],
    ['scripts/tests/ralph.py'],
    ['scripts/tests/agent_exec_runtime.py'],
    ['scripts/tests/capabilities_runtime.py'],
    ['scripts/tests/doclinks.py'],
    ['scripts/tests/doclinks_cases.py'],
]


SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(SCRIPTS_DIR))
BINARY = os.path.join('target', 'debug', 'ah')


def script_name(entry):
    """Suite name for an entry: the script basename without directory or suffix."""
    return os.path.splitext(os.path.basename(entry[0]))[0]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--list', action='store_true', help='print the suites in order, one per line')
    parser.add_argument('suites', nargs='*', metavar='SUITE',
                        help='script names to run (e.g. preview single_runtime); all suites by default')
    args = parser.parse_args(argv)
    if args.list:
        for suite in SUITES:
            print(' '.join(suite))
        return 0

    known = {script_name(suite) for suite in SUITES}
    unknown = [name for name in args.suites if name not in known]
    if unknown:
        parser.error('unknown suite(s): %s; known suites: %s'
                     % (', '.join(unknown), ', '.join(sorted(known))))

    if args.suites:
        selected = [suite for suite in SUITES if script_name(suite) in set(args.suites)]
    else:
        selected = SUITES

    if not os.path.exists(os.path.join(REPO_ROOT, BINARY)):
        print('error: %s is missing; run `cargo build --locked` first' % BINARY, file=sys.stderr)
        return 2

    failed = 0
    for entry in selected:
        label = ' '.join(entry)
        started = time.monotonic()
        completed = subprocess.run([sys.executable, *entry], cwd=REPO_ROOT)
        elapsed = time.monotonic() - started
        if completed.returncode == 0:
            print('PASS %s (%.1fs)' % (label, elapsed), flush=True)
        else:
            print('FAIL %s (exit %s, %.1fs)' % (label, completed.returncode, elapsed), flush=True)
            failed += 1
    print('%d/%d passed' % (len(selected) - failed, len(selected)))
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
