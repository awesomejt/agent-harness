#!/usr/bin/env python3
"""Fake-only P7.10 ACP candidate; never launches installed OpenCode or real keys."""
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
FAKE = ROOT / 'scripts/tests/fake_opencode.py'
CASES = {
    'success': (0, True),
    'go-limit-rpc': (4, True),
    'go-tool-event': (1, True),
    'route': (2, False),
    'go-baseurl': (2, False),
    'go-title-missing': (2, False),
    'native-provider': (2, False),
    'native-enabled': (2, False),
    'native-agent': (2, False),
    'agent-model': (2, False),
    'project-source': (2, False),
    'catalog-foreign': (2, False),
    'session-model': (1, False),
}

for case, (expected, prompted) in CASES.items():
    with tempfile.TemporaryDirectory(prefix='ah-p710-fixture-') as temporary:
        project = Path(temporary).resolve()
        (project / 'opencode').symlink_to(FAKE)
        (project / 'case').write_text(case)
        (project / 'track-runtime-home').touch()
        env = dict(os.environ, PATH=str(project) + os.pathsep + os.environ['PATH'],
                   P710_KEY='SECRET_SENTINEL', AH_P710_PROJECT=str(project),
                   OPENCODE_API_KEY='poison', LITELLM_API_KEY='poison')
        result = subprocess.run(
            ['cargo', 'test', '--locked', '--lib', 'runtime::go_candidate_fixture::synthetic_acp',
             '--', '--ignored', '--exact', '--nocapture'],
            cwd=ROOT, env=env, capture_output=True, text=True, timeout=60)
        output = result.stdout + result.stderr
        assert result.returncode == 0, (case, result.returncode, output)
        assert f'P710_RESULT={expected}' in output, (case, output)
        assert 'SECRET_SENTINEL' not in output and 'poison' not in output, case
        assert (project / 'prompted').exists() == prompted, case
        if (project / 'launch-routes').exists():
            assert (project / 'launch-routes').read_text().splitlines() == ['native'], case
        assert not Path((project / 'runtime-home').read_text()).exists(), case

# The live entry point must refuse without the explicit gate, a real key, or
# the installed executable. Dummy values prevent these checks contacting Go.
for ack, key, refusal in [
        ('absent', 'NOT_A_REAL_KEY', 'left: Ok("absent")'),
        ('operator-attested', 'SECRET_SENTINEL', 'assertion `left != right` failed'),
        ('operator-attested', 'NOT_A_REAL_KEY', f'left: "{FAKE.resolve()}"')]:
    with tempfile.TemporaryDirectory(prefix='ah-p710-refusal-') as temporary:
        project = Path(temporary).resolve()
        (project / 'opencode').symlink_to(FAKE)
        (project / 'case').write_text('success')
        env = dict(os.environ, PATH=str(project) + os.pathsep + os.environ['PATH'],
                   P710_KEY=key, AH_P710_LIVE=ack)
        result = subprocess.run(
            ['cargo', 'test', '--locked', '--lib', 'runtime::go_candidate_fixture::live_acp',
             '--', '--ignored', '--exact', '--nocapture'],
            cwd=ROOT, env=env, capture_output=True, text=True, timeout=60)
        assert result.returncode == 101 and 'P710_LIVE_RESULT=' not in result.stdout
        assert refusal in result.stderr, (ack, refusal, result.stderr)
print(f'PASS {len(CASES)} Go ACP candidate fixtures and 3 live-entry refusals; fake runtime only')
