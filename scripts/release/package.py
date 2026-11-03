#!/usr/bin/env python3
"""Build the reviewed, locked Apple Silicon macOS prerelease (maintainers only)."""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import platform
import posixpath
import re
import shutil
import subprocess
import tarfile
import tempfile
import tomllib

ROOT = Path(__file__).resolve().parents[2]
TARGET = 'aarch64-apple-darwin'
REVIEWED_LICENSES = {
    'MIT': 'MIT',
    'Apache-2.0': 'Apache-2.0',
    'MIT OR Apache-2.0': 'MIT',
    'Apache-2.0 OR MIT': 'MIT',
    'MIT/Apache-2.0': 'MIT',
    'Unlicense OR MIT': 'MIT',
    'Zlib OR Apache-2.0 OR MIT': 'MIT',
    'Apache-2.0 OR BSL-1.0': 'Apache-2.0',
    '(MIT OR Apache-2.0) AND Unicode-3.0': 'MIT AND Unicode-3.0',
    'Unicode-3.0': 'Unicode-3.0',
}


def select_license(expression):
    if expression not in REVIEWED_LICENSES:
        raise RuntimeError(f'unreviewed license: {expression}')
    return REVIEWED_LICENSES[expression]


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
    if run('rustc', '+1.88.0', '--version').split()[1] != '1.88.0':
        parser.error('Rust 1.88.0 is required')
    package = tomllib.loads((ROOT / 'Cargo.toml').read_text())['package']
    version = package['version']
    commit = run('git', 'rev-parse', 'HEAD')
    # Keep registry caches, but refuse ambient compiler/linker/profile overrides.
    overrides = [name for name in os.environ if name.startswith(
        ('CARGO_TARGET_', 'CARGO_PROFILE_', 'CARGO_BUILD_', 'RUSTC_', 'RUSTDOC'))
        or name in ('RUSTFLAGS', 'CARGO_ENCODED_RUSTFLAGS', 'RUSTC',
                    'MACOSX_DEPLOYMENT_TARGET', 'SDKROOT')]
    if overrides:
        raise RuntimeError('unset build override variable names: ' + ', '.join(sorted(overrides)))
    args.output.mkdir(parents=True, exist_ok=False)
    try:
        with tempfile.TemporaryDirectory(prefix='ah-release-build-') as build_directory:
            build_package(args.output, version, commit, Path(build_directory))
    except BaseException:
        # This invocation exclusively created the output directory above.
        shutil.rmtree(args.output)
        raise


def build_package(output_directory, version, commit, build_directory):
    env = dict(os.environ, MACOSX_DEPLOYMENT_TARGET='14.0', RUSTFLAGS='',
               CARGO_ENCODED_RUSTFLAGS='', CARGO_PROFILE_RELEASE_STRIP='none',
               CARGO_TARGET_DIR=str(build_directory))
    subprocess.run(['cargo', '+1.88.0', 'build', '--release', '--locked', '--target', TARGET],
                   cwd=ROOT, env=env, check=True)
    metadata = json.loads(run('cargo', '+1.88.0', 'metadata', '--locked', '--format-version', '1',
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
        binary = build_directory / TARGET / 'release/ah'
        shutil.copy2(binary, bundle / 'ah')
        architecture = run('/usr/bin/lipo', '-archs', str(binary))
        build_version = run('/usr/bin/xcrun', 'vtool', '-show-build', str(binary))
        if architecture != 'arm64' or not any(
                line.split() == ['minos', '14.0'] for line in build_version.splitlines()):
            raise RuntimeError('unexpected Mach-O architecture or deployment target')
        dylibs = run('/usr/bin/otool', '-L', str(binary))
        for line in dylibs.splitlines()[1:]:
            if not line.strip().startswith(('/usr/lib/', '/System/Library/')):
                raise RuntimeError(f'unbundled non-system library: {line}')
        for source, target in [('LICENSE', 'LICENSE'), ('docs/OPERATIONS.md', 'INSTALL.md'),
                               ('scripts/release/NOTICES.md', 'THIRD_PARTY_NOTICES.md')]:
            shutil.copy2(ROOT / source, bundle / target)
        # Sample configs and canonical agents, validated by tests and the archive smoke.
        examples = bundle / 'examples'
        (examples / 'agents').mkdir(parents=True)
        for path in sorted((ROOT / 'examples').glob('ah.*.json')):
            shutil.copy2(path, examples / path.name)
        for path in sorted((ROOT / 'agents').glob('*.md')):
            shutil.copy2(path, examples / 'agents' / path.name)
        install = bundle / 'INSTALL.md'
        def repository_link(match):
            target = match.group(2)
            if ':' in target or target.startswith(('#', '/')):
                return match.group(0)
            path = posixpath.normpath('docs/' + target)
            return f'[{match.group(1)}](https://github.com/awesomejt/agent-harness/blob/{commit}/{path})'
        install.write_text(re.sub(r'\[([^\]]+)\]\(([^)]+)\)', repository_link,
                                  install.read_text()))
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
            selected = select_license(license_expression)
            inventory.append(dict(name=dep['name'], version=dep['version'], selected_license=selected,
                                  license=dep['license'], source=dep['source'], sha256=checksum))
        shutil.copytree(ROOT / 'scripts/release/licenses', notices / 'supplemental')
        rust_docs = Path(run('rustc', '+1.88.0', '--print', 'sysroot')) / 'share/doc/rust'
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
                    cargo_lock_sha256=sha(ROOT / 'Cargo.lock'), rustc=run('rustc', '+1.88.0', '-Vv'),
                    cargo=run('cargo', '+1.88.0', '-V'), architecture=architecture,
                    macho_build_version='\n'.join(build_version.splitlines()[1:]),
                    macos=platform.mac_ver()[0], deployment_target='14.0', strip='none',
                    linker=run('xcodebuild', '-version'), dylibs='\n'.join(dylibs.splitlines()[1:]),
                    binary_sha256=sha(bundle / 'ah'), registry_packages=len(inventory))
        (bundle / 'BUILD-INFO.json').write_text(json.dumps(info, indent=2) + '\n')
        output = output_directory / f'{name}.tar.gz'
        epoch = int(run('git', 'show', '-s', '--format=%ct', commit))
        def normalize(entry):
            entry.uid = entry.gid = 0
            entry.uname = entry.gname = ''
            entry.mtime = epoch
            entry.pax_headers = {}
            return entry
        with output.open('xb') as raw:
            with gzip.GzipFile(filename='', fileobj=raw, mode='wb', mtime=epoch) as compressed:
                with tarfile.open(fileobj=compressed, mode='w') as archive:
                    archive.add(bundle, arcname=name, filter=normalize)
        (output_directory / 'SHA256SUMS').write_text(f'{sha(output)}  {output.name}\n')
    print(output.resolve())


if __name__ == '__main__':
    main()
