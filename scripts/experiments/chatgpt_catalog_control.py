#!/usr/bin/env python3
"""Disposable no-auth explicit-catalog/cache proof. No retained-root argument or login support."""
import argparse
import copy
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import sqlite3
import stat
import sys
import tempfile

from antigravity_feasibility import check
from chatgpt_catalog_audit import audit
from chatgpt_contained import owned_server
from chatgpt_feasibility import SHA256
from chatgpt_installed_observer import (
    PYTHON, ancestor_denials, combined_profile, expected_plugins, fresh_port,
    log_inventory, static_guards, verify_source,
)
from chatgpt_method_endpoint_helper import MethodProofObserver
from chatgpt_retained_state import (
    PUBLISHED_INTEGRATION_COUNT, PUBLISHED_INTEGRATION_DIGEST, acquire,
    config_documents, database_path, integration_digest, lock_probe, new_case,
    preflight, resources_ready, root_shape, settle_view,
)

CATALOG = 'owned.catalog'
PROBE_PROVIDER = 'abacus'
PROBE_MODEL = 'ah-catalog-probe'
EXTRA = 'ah-synthetic-cache'
KEY = 'models-dev:v2:catalog'


def digest(value):
    return hashlib.sha256(value).hexdigest()


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def catalogs(packages):
    """Pinned source snapshot plus a public, non-secret probe with .invalid endpoints."""
    explicit = json.loads((packages / 'core/src/models-dev/snapshot.txt').read_bytes())
    model = {'id': PROBE_MODEL, 'type': 'chat', 'name': 'AH explicit model',
             'release_date': '2026-01-01', 'modalities': {'input': ['text'], 'output': ['text']},
             'capabilities': {'tools': {'supported': True}, 'reasoning': {'supported': False}},
             'limit': {'context': 4096, 'output': 1024},
             'api': {'chat-completions': {'base_url': 'https://explicit.invalid/v1',
                     'sdk': {'opencodeai': '@opencode/ai/providers/openai-compatible'}}}}
    explicit[PROBE_PROVIDER].update(name='AH explicit provider', models={PROBE_MODEL: model})
    cached = copy.deepcopy(explicit)
    cached[PROBE_PROVIDER]['name'] = 'AH cached provider'
    cached[PROBE_PROVIDER]['models'][PROBE_MODEL]['name'] = 'AH cached model'
    cached[PROBE_PROVIDER]['models'][PROBE_MODEL]['api']['chat-completions']['base_url'] = 'https://cached.invalid/v1'
    cached[EXTRA] = copy.deepcopy(cached[PROBE_PROVIDER])
    cached[EXTRA].update(id=EXTRA, name='AH extra cached provider', env=['AH_SYNTHETIC_CACHE_KEY'])
    return encoded(explicit), encoded(cached)


def owned_file(path, work):
    """No symlinks, hard links or paths outside the newly minted experiment root."""
    check(path.is_absolute() and work.resolve() == work and path.resolve() == path and work in path.parents)
    for parent in [path.parent, *path.parent.parents]:
        if parent == work.parent:
            break
        check(not parent.is_symlink() and parent.is_dir() and parent.stat().st_uid == os.getuid())
    info = path.lstat()
    check(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and info.st_uid == os.getuid())


def catalog_guard(ctx, expected):
    work, env = ctx['work'], ctx['env']
    check(not root_shape(work, ctx['token'], env))
    path = work / CATALOG
    owned_file(path, work)
    body = path.read_bytes()
    check(digest(body) == expected and isinstance(json.loads(body), dict))
    # The existing environment/source allowlist remains unchanged everywhere else.
    plain = dict(env)
    check(plain.pop('OPENCODE_MODELS_PATH', None) == str(path))
    static_guards(work, ctx['home'], ctx['project'], plain)
    check(env['OPENCODE_DISABLE_MODELS_FETCH'] == 'true')
    return path


def install_catalog(ctx, body):
    path = ctx['work'] / CATALOG
    with path.open('xb') as output:
        output.write(body)
    ctx['env']['OPENCODE_MODELS_PATH'] = str(path)
    # Explicit activation exposes metadata only; no connection, key or session is created.
    content = json.loads(ctx['env']['OPENCODE_CONFIG_CONTENT'])
    content['providers'] = {PROBE_PROVIDER: {'activation': 'enabled'}}
    content['model'] = {'providerID': PROBE_PROVIDER, 'model': PROBE_MODEL}
    ctx['env']['OPENCODE_CONFIG_CONTENT'] = json.dumps(content)


class CatalogObserver(MethodProofObserver):
    # Only these metadata reads are added; never a session, KV, auth or refresh route.
    allowed = dict(MethodProofObserver.allowed, **{'/api/provider/abacus': 'object'})


def probe(observer, mode):
    provider = observer.get('/api/provider/abacus')
    model = observer.get('/api/model/default')
    check(provider['id'] == PROBE_PROVIDER and provider['name'] == f'AH {mode} provider')
    check(provider['package'] == '@opencode/ai/providers/openai-compatible')
    check(provider.get('settings') == {'baseURL': f'https://{mode}.invalid/v1'})
    check(model['providerID'] == PROBE_PROVIDER and model['id'] == PROBE_MODEL)
    check(model['name'] == f'AH {mode} model' and model['limit']['context'] == 4096)
    check(model['settings']['baseURL'] == f'https://{mode}.invalid/v1')
    return digest(encoded([provider, model]))


def boot(ctx, expected_hash, mode='explicit', cached=False):
    path = catalog_guard(ctx, expected_hash)
    work, project, runtime = ctx['work'], ctx['project'], ctx['runtime']
    port = fresh_port()
    env = dict(ctx['env'], OPENCODE_PASSWORD=secrets.token_urlsafe(32))
    policy = combined_profile(work, port, ancestor_denials(ctx['home']))
    policy += '(deny file-write* (literal ' + json.dumps(str(path)) + '))'
    check(database_path(runtime, project, env, policy, work))
    log = work / 'DATA/opencode/log/opencode.log'
    offset = len(log.read_text().splitlines()) if log.exists() else 0
    # The cache control intentionally omits the explicit-file option, on synthetic state only.
    if cached:
        env.pop('OPENCODE_MODELS_PATH')
    with owned_server(runtime, project, env, policy, port) as url:
        observer = CatalogObserver(port, env['OPENCODE_PASSWORD'], project)
        check(observer.locations() == [])
        resources, integrations, identities = settle_view(observer, (work,), resources_ready(ctx['builtin']))
        documents = config_documents(runtime, project, env, policy, url, (work,))
        check(not identities)
        check(all(not connections for _, connections in integrations.values()))
        expected_set = set(ctx['baseline_ids']) | ({EXTRA} if cached else set())
        check(set(integrations) == expected_set)
        check(not preflight(integrations, resources, documents, expected_set, ctx['builtin'], login=False))
        violations = preflight(integrations, resources, documents, set(ctx['baseline_ids']), ctx['builtin'], login=False)
        check(violations == (['integration-set'] if cached else []))
        metadata = probe(observer, mode)
        check(observer.locations() == [str(project)])
    catalog_guard(ctx, expected_hash)
    watches, spawns, problems = log_inventory('\n'.join(log.read_text().splitlines()[offset:]), work)
    check(not problems and set(spawns) <= {('git', 'rev-parse')})
    check(not any(message == 'watcher failed' for _, _, message in watches))
    check(('MACHINE_PARENT', 'entries', 'watcher started') in watches)
    check(not any(path.name == 'node_modules' for path in work.rglob('*')))
    check(not any((work / 'denied-bin').iterdir()))
    return {'count': len(integrations), 'ids_sha256': integration_digest(integrations),
            'metadata_sha256': metadata, 'fixed_gate_refusals': violations,
            'resources_sha256': digest(encoded(resources)),
            'integration_methods_sha256': digest(encoded(integrations))}


def static_cases(ctx, body):
    path, expected = ctx['work'] / CATALOG, digest(body)
    refused = []
    def refuse(name):
        try:
            catalog_guard(ctx, expected)
        except (RuntimeError, OSError, ValueError):
            refused.append(name)
        else:
            raise AssertionError('catalog mutation accepted')
    path.unlink()
    refuse('missing')
    path.write_bytes(b'{')
    refuse('malformed')
    changed = json.loads(body)
    changed[PROBE_PROVIDER]['name'] = 'AH same-ID changed metadata'
    path.write_bytes(encoded(changed))
    refuse('same-ID-metadata')
    path.write_bytes(body + b' ')
    refuse('changed-bytes')
    path.unlink()
    target = ctx['work'] / 'link-target.catalog'
    target.write_bytes(body)
    path.symlink_to(target)
    refuse('symlink')
    path.unlink()
    os.link(target, path)
    refuse('hardlink')
    path.unlink()
    target.unlink()
    path.write_bytes(body)
    catalog_guard(ctx, expected)
    return refused


def run(runtime, packages, builtin, baseline_ids):
    """All database operations are scoped to this function's newly created temporary root.

    There is no attach/root/database argument. The only write is one synthetic catalog KV
    key after the first no-auth boot has stopped. No credential or other row is queried.
    """
    explicit, cached = catalogs(packages)
    with tempfile.TemporaryDirectory(prefix='ah-catalog-control-') as directory:
        ctx = new_case(Path(directory).resolve(), runtime, builtin)
        ctx['baseline_ids'] = baseline_ids
        install_catalog(ctx, explicit)
        held = acquire(ctx['work'])
        check(held is not None)
        try:
            check(lock_probe(ctx['work']) == 'refused')
            first = boot(ctx, digest(explicit))
            check(first['count'] == PUBLISHED_INTEGRATION_COUNT and first['ids_sha256'] == PUBLISHED_INTEGRATION_DIGEST)
            refusals = static_cases(ctx, explicit)
            check(boot(ctx, digest(explicit)) == first)
            db = ctx['work'] / 'DATA/opencode/opencode.db'
            owned_file(db, ctx['work'])
            # mode=rw cannot silently create another database. SQL and key are fixed.
            with closing(sqlite3.connect(db.as_uri() + '?mode=rw', uri=True)) as connection, connection:
                try:
                    connection.execute('INSERT INTO kv (key,value,time_created,time_updated) VALUES (?,?,?,?)',
                                       (KEY, json.dumps({'updatedAt': 1, 'body': cached.decode()}), 1, 1))
                except sqlite3.IntegrityError:
                    raise RuntimeError('synthetic catalog key pre-exists') from None
            # Prove the seed is effective (not merely a syntactically accepted write).
            cache_a = boot(ctx, digest(explicit), mode='cached', cached=True)
            cache_b = boot(ctx, digest(explicit), mode='cached', cached=True)
            check(cache_a == cache_b and cache_a['metadata_sha256'] != first['metadata_sha256'])
            # Same retained synthetic database, now with the explicit file, across two boots.
            explicit_a = boot(ctx, digest(explicit))
            check(boot(ctx, digest(explicit), mode='cached', cached=True) == cache_a)
            explicit_b = boot(ctx, digest(explicit))
            check(first == explicit_a == explicit_b)
            check(boot(ctx, digest(explicit), mode='cached', cached=True) == cache_a)
            check(lock_probe(ctx['work']) == 'refused')
        finally:
            os.close(held)
        check(lock_probe(ctx['work']) == 'acquired')
    return {'explicit_catalog_sha256': digest(explicit), 'cached_catalog_sha256': digest(cached),
            'static_refusals': refusals, 'fresh_and_explicit': first, 'cache_control': cache_a,
            'two_boots_equal': True, 'synthetic_seed_only': True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--opencode', default='opencode')
    args = parser.parse_args()
    check(sys.platform == 'darwin' and Path(PYTHON).is_file() and Path('/usr/bin/sandbox-exec').is_file())
    audit(args.source)
    packages, _ = verify_source(args.source.resolve())
    builtin, _, _ = expected_plugins(packages)
    from chatgpt_retained_state import literal_integrations, plugin_files, snapshot_providers, boundary_controls
    baseline_ids = snapshot_providers(packages) | set(literal_integrations(packages, plugin_files(packages)))
    installed = shutil.which(args.opencode)
    check(installed is not None)
    with tempfile.TemporaryDirectory(prefix='ah-catalog-bin-') as directory:
        parent = Path(directory).resolve()
        runtime = parent / 'opencode-cli'
        shutil.copy2(installed, runtime)
        if digest(runtime.read_bytes()) != SHA256:
            raise RuntimeError('executable pin mismatch')
        boundary_controls(parent)
        results = run(runtime, packages, builtin, baseline_ids)
    print(json.dumps(results, indent=2, sort_keys=True))
    print('LIMIT: disposable no-auth proof only; authenticated helpers and feasibility gates unchanged')


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        reason = str(error) if str(error) in {'synthetic catalog key pre-exists', 'executable pin mismatch'} else 'raw diagnostics withheld'
        print('Catalog control proof failed; ' + reason, file=sys.stderr)
        sys.exit(1)
