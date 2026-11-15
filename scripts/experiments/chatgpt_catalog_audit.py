#!/usr/bin/env python3
"""Pinned public-source and synthetic ID audit; never opens a runtime or retained state."""
import argparse
import hashlib
import json
from pathlib import Path

from antigravity_feasibility import check
from chatgpt_installed_observer import verify_source
from chatgpt_retained_state import (
    FINGERPRINTS, PUBLISHED_INTEGRATION_COUNT, PUBLISHED_INTEGRATION_DIGEST,
    integration_digest, literal_integrations, plugin_files, snapshot_providers,
)


CATALOG_FINGERPRINTS = {
    'core/src/models-dev.ts': '1f96a4848a56bfc6904e8831af15de14ae0af86c12228578801593b73df79d00',
    'core/script/models-snapshot.ts': '529ebb780f151cbec2841e08de2693e8bbac660543cc7fad19970a7aff3363ca',
    'cli/script/build.ts': '1011c2c8cfad6fb3f81d8fa26c6ceef764a64a3d7efddd8fff05fcb7186c1fa1',
    'core/src/kv.ts': '40f41ca6c6d77cf42b64c1ec1e535a306b8355740f62a7b59d762068ad153e36',
    'core/src/kv/sql.ts': 'c2f86325662f1070fb31e0c7b6058a8fc678978d806c86b1ef973befaba41627',
}


def audit(source):
    packages, fingerprints = verify_source(source.resolve())
    for name, expected in dict(FINGERPRINTS, **CATALOG_FINGERPRINTS).items():
        digest = hashlib.sha256((packages / name).read_bytes()).hexdigest()
        check(digest == expected)
        fingerprints[name] = digest
    files = plugin_files(packages)
    literals = set(literal_integrations(packages, files))
    catalog = snapshot_providers(packages)
    baseline = catalog | literals
    check(len(baseline) == PUBLISHED_INTEGRATION_COUNT)
    check(integration_digest(baseline) == PUBLISHED_INTEGRATION_DIGEST)

    # Projections over synthetic provider IDs, not a reimplementation of ModelsDev.normalize
    # or a claim that the installed runtime accepts a particular catalog payload.
    added = {f'ah-synthetic-catalog-{index:03d}' for index in range(100)}
    check(not added & baseline)
    expanded = baseline | added
    substituted = (baseline - {sorted(baseline)[0]}) | {sorted(added)[0]}
    for changed in (expanded, substituted):
        check(integration_digest(changed) != PUBLISHED_INTEGRATION_DIGEST)
    check(len(expanded) == 336 and len(substituted) == len(baseline))
    check(integration_digest(reversed(sorted(baseline))) == PUBLISHED_INTEGRATION_DIGEST)
    return {
        'fingerprints': fingerprints,
        'baseline': {'snapshot_env_providers': len(catalog), 'plugin_named': len(literals),
                     'plugin_only': sorted(literals - catalog), 'count': len(baseline),
                     'sha256': integration_digest(baseline)},
        'synthetic_id_projections': {
            'added_100': {'count': len(expanded), 'fixed_digest_matches': False},
            'same_count_substitution': {'count': len(substituted), 'fixed_digest_matches': False},
            'reordered_baseline': {'fixed_digest_matches': True},
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True, help='clean official v2.2.5 checkout')
    args = parser.parse_args()
    print(json.dumps(audit(args.source), indent=2, sort_keys=True))
    print('LIMIT: source audit and synthetic ID projections only; no installed catalog/cache proof')


if __name__ == '__main__':
    main()
