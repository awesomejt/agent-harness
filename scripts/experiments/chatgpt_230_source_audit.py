#!/usr/bin/env python3
"""Read-only OpenCode 2.3.0 public-source qualification; no runtime/state/network access."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

from antigravity_feasibility import check
from chatgpt_installed_observer import array_entries, imports, module_file, resolve_entries
from chatgpt_retained_state import (
    PUBLISHED_INTEGRATION_COUNT, PUBLISHED_INTEGRATION_DIGEST,
    integration_digest, literal_integrations, snapshot_providers,
)

PIN = 'a6b15d33daf6ab7d35569f6d711fdb630b9f04e7'
MANIFEST = Path(__file__).resolve().parents[2] / 'docs/evidence/p7-9-230-source-manifest.json'


def websearch_registrations(text):
    """Pinned register(ctx, {id: literal, ...}) calls, not arbitrary object IDs."""
    calls = text.count('WebSearchProvider.register(')
    ids = re.findall(r'WebSearchProvider\.register\(ctx,\s*\{\s*id:\s*"([a-z0-9-]+)"\s*,', text)
    check(len(ids) == calls and len(ids) == len(set(ids)))
    return ids


def derive(packages):
    internal = packages / 'core/src/plugin/internal.ts'
    seen, ids = {internal}, []
    for group in ('pre', 'post'):
        ids += resolve_entries(packages, internal, array_entries(internal.read_text(), group), seen)
    check(len(ids) == len(set(ids)))
    plugin_files = sorted(seen)
    # Match the existing literal audit's one-hop relative import boundary. Hash
    # every byte it can consume, plus package exports used by module resolution.
    for path in plugin_files:
        _, table = imports(packages, path)
        seen |= {module_file(packages, path, spec) for spec, _ in table.values()
                 if spec.startswith('.') and spec.endswith('.js')}
    seen |= set(packages.glob('*/package.json'))
    # These are read by literal_integrations/provider_constants and snapshot_providers.
    seen |= {packages / 'schema/src/provider.ts', packages / 'core/src/models-dev/snapshot.txt'}
    names = literal_integrations(packages, plugin_files)
    # 2.3.0 moved five web-search integrations into this shared registration factory.
    # Its body is hash-pinned along with every call site; this is a finite source
    # projection, not a general TypeScript interpreter or installed proof.
    for path in plugin_files:
        for name in websearch_registrations(path.read_text()):
            names.setdefault(name, set()).add(str(path.relative_to(packages)))
    catalog = snapshot_providers(packages)
    projected = catalog | set(names)
    check(len(projected) == PUBLISHED_INTEGRATION_COUNT)
    check(integration_digest(projected) == PUBLISHED_INTEGRATION_DIGEST)
    return {
        'plugins': {'ids': sorted(ids), 'files': len(plugin_files),
                    'sha256': hashlib.sha256(b''.join(p.read_bytes() for p in plugin_files)).hexdigest()},
        'integrations': {'snapshot_env_providers': len(catalog), 'plugin_named': len(names),
                         'plugin_only': sorted(set(names) - catalog), 'count': len(projected),
                         'sha256': integration_digest(projected),
                         'provenance': {key: sorted(value) for key, value in sorted(names.items())}},
    }, seen


def verify_files(packages, files):
    check(isinstance(files, dict) and bool(files))
    for name, expected in files.items():
        relative = Path(name)
        check(not relative.is_absolute() and '..' not in relative.parts)
        path = packages / relative
        check(path.is_file() and path.resolve() == path and not path.is_symlink())
        check(hashlib.sha256(path.read_bytes()).hexdigest() == expected)


def audit(source):
    source = source.resolve()
    for args, expected in ((['rev-parse', 'HEAD'], PIN), (['status', '--porcelain'], '')):
        result = subprocess.run(['/usr/bin/git', '-C', str(source), *args],
                                capture_output=True, text=True, timeout=30)
        check(result.returncode == 0 and result.stdout.strip() == expected)
    manifest = json.loads(MANIFEST.read_text())
    check(manifest['source_commit'] == PIN and manifest['kind'] == 'p7-9-230-source/v1')
    packages = source / 'packages'
    verify_files(packages, manifest['files'])
    observation, consumed = derive(packages)
    check(observation == manifest['observation'])
    check({str(p.relative_to(packages)) for p in consumed} <= set(manifest['files']))
    return {'source_commit': PIN, 'verified_files': len(manifest['files']), **observation}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True, help='clean official v2.3.0 checkout')
    args = parser.parse_args()
    print(json.dumps(audit(args.source), indent=2, sort_keys=True))
    print('LIMIT: source qualification only; installed containment, catalog and login gates remain open')


if __name__ == '__main__':
    main()
