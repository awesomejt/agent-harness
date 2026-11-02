#!/usr/bin/env python3
"""Build the reviewed, locked Apple Silicon macOS prerelease (maintainers only)."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import tarfile
import tempfile
import tomllib

ROOT = Path(__file__).resolve().parents[2]
TARGET = 'aarch64-apple-darwin'


def run(*args, env=None):
    return subprocess.check_output(args, cwd=ROOT, env=env, text=True).strip()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path, help='new output directory')
    args = parser.parse_args()
    if platform.system() != 'Darwin' or platform.machine() != 'arm64':
        parser.error('build and test on native Apple Silicon macOS only')
    if run('git', 'status', '--porcelain'):
        parser.error('commit all source changes before packaging')
    if run('rustc', '--version').split()[1] != '1.88.0':
        parser.error('Rust 1.88.0 is required')
    package = tomllib.loads((ROOT / 'Cargo.toml').read_text())['package']
    version = package['version']
    commit = run('git', 'rev-parse', 'HEAD')
    args.output.mkdir(parents=True, exist_ok=False)
    env = dict(os.environ, MACOSX_DEPLOYMENT_TARGET='14.0', RUSTFLAGS='',
               CARGO_ENCODED_RUSTFLAGS='', CARGO_TARGET_DIR=str(ROOT / 'target/release-build'))
    subprocess.run(['cargo', 'build', '--release', '--locked', '--target', TARGET],
                   cwd=ROOT, env=env, check=True)
    metadata = json.loads(run('cargo', 'metadata', '--locked', '--format-version', '1',
                              '--filter-platform', TARGET, env=env))
    ids = {node['id'] for node in metadata['resolve']['nodes']}
    dependencies = sorted((p for p in metadata['packages'] if p['id'] in ids and p['source']),
                          key=lambda p: (p['name'], p['version']))
    lock = tomllib.loads((ROOT / 'Cargo.lock').read_text())
    checksums = {(p['name'], p['version']): p.get('checksum') for p in lock['package']}
    name = f'ah-v{version}-{TARGET}'
    with tempfile.TemporaryDirectory(prefix='ah-package-') as temporary:
        bundle = Path(temporary) / name
        bundle.mkdir()
        binary = ROOT / 'target/release-build' / TARGET / 'release/ah'
        shutil.copy2(binary, bundle / 'ah')
        dylibs = run('otool', '-L', str(binary))
        for line in dylibs.splitlines()[1:]:
            if not line.strip().startswith(('/usr/lib/', '/System/Library/')):
                raise RuntimeError(f'unbundled non-system library: {line}')
        for source, target in [('LICENSE', 'LICENSE'), ('docs/OPERATIONS.md', 'INSTALL.md'),
                               ('scripts/release/NOTICES.md', 'THIRD_PARTY_NOTICES.md')]:
            shutil.copy2(ROOT / source, bundle / target)
        notices = bundle / 'third-party'
        sources = notices / 'sources'
        sources.mkdir(parents=True)
        inventory = []
        embedded = {
            'futures-channel': ['src/mpsc/queue.rs'],
            'schemars': ['src/_private/regex_syntax.rs'],
            'serde_json': ['src/lexical/mod.rs'],
        }
        for dep in dependencies:
            manifest = Path(dep['manifest_path'])
            # Cargo registry src/<registry>/<crate>/Cargo.toml -> cache/<registry>/<crate>.crate
            registry = manifest.parents[1].name
            archive = manifest.parents[3] / 'cache' / registry / f"{dep['name']}-{dep['version']}.crate"
            checksum = sha(archive)
            if checksum != checksums[(dep['name'], dep['version'])]:
                raise RuntimeError(f'archive checksum mismatch: {archive.name}')
            shutil.copy2(archive, sources / archive.name)
            # Also expose license/copyright/NOTICE files without needing source extraction.
            crate_notices = notices / f"{dep['name']}-{dep['version']}"
            for path in sorted(manifest.parent.rglob('*')):
                if path.is_file() and any(word in path.name.lower() for word in
                                          ('license', 'licence', 'copyright', 'notice', 'copying')):
                    dest = crate_notices / path.relative_to(manifest.parent)
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(path, dest)
            if not crate_notices.exists() and (dep['name'], dep['version']) != (
                    'agent-client-protocol-schema', '1.13.0'):
                raise RuntimeError(f"missing attribution files: {dep['name']}")
            for relative in embedded.get(dep['name'], []):
                dest = crate_notices / 'embedded-notices' / relative
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(manifest.parent / relative, dest)
            license_expression = dep['license'] or ''
            if 'MIT' in license_expression:
                selected = 'MIT'
                if 'AND Unicode-3.0' in license_expression:
                    selected += ' AND Unicode-3.0'
            elif 'Apache-2.0' in license_expression:
                selected = 'Apache-2.0'
            elif license_expression == 'Unicode-3.0':
                selected = 'Unicode-3.0'
            else:
                raise RuntimeError(f'unreviewed license: {license_expression}')
            inventory.append(dict(name=dep['name'], version=dep['version'], selected_license=selected,
                                  license=dep['license'], source=dep['source'], sha256=checksum))
        shutil.copytree(ROOT / 'scripts/release/licenses', notices / 'supplemental')
        rust_docs = Path(run('rustc', '--print', 'sysroot')) / 'share/doc/rust'
        rust_notices = notices / 'rust-1.88.0'
        rust_notices.mkdir()
        for path in rust_docs.iterdir():
            if path.name.startswith(('COPYRIGHT', 'LICENSE')) or path.name == 'licenses':
                if path.is_dir():
                    shutil.copytree(path, rust_notices / path.name)
                else:
                    shutil.copy2(path, rust_notices / path.name)
        if not (rust_notices / 'COPYRIGHT-library.html').is_file():
            raise RuntimeError('missing Rust standard-library notices')
        (notices / 'inventory.json').write_text(json.dumps(inventory, indent=2) + '\n')
        info = dict(version=version, source_commit=commit, target=TARGET,
                    cargo_lock_sha256=sha(ROOT / 'Cargo.lock'), rustc=run('rustc', '-Vv'),
                    macos=platform.mac_ver()[0], deployment_target='14.0',
                    linker=run('xcodebuild', '-version'), dylibs=dylibs,
                    binary_sha256=sha(bundle / 'ah'), registry_packages=len(inventory))
        (bundle / 'BUILD-INFO.json').write_text(json.dumps(info, indent=2) + '\n')
        output = args.output / f'{name}.tar.gz'
        with tarfile.open(output, 'w:gz') as archive:
            archive.add(bundle, arcname=name)
        (args.output / 'SHA256SUMS').write_text(f'{sha(output)}  {output.name}\n')
    print(output.resolve())


if __name__ == '__main__':
    main()
