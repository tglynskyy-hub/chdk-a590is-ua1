#!/usr/bin/env python3
"""Validate upstream full distribution, then produce a deterministic SD ZIP."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import tempfile
import zipfile
from functools import lru_cache
import audit_modules

ROOT = Path(__file__).resolve().parents[2]
FLAVOR = 'diagnostic' if os.environ.get('UI_PROFILE') == '1' else 'normal'
NAME = 'CHDK-A590IS-101B-1.7.0-r6346-task004b-' + FLAVOR + '-full.zip'
IDENTITY = {'platform': 'a590', 'firmware': '101b', 'chdk': '1.7.0', 'svn': 6346, 'variant': 'enhanced-task004b', 'build_mode': FLAVOR, 'conf_abi': [3, 7]}


@lru_cache(maxsize=1)
def module_inventory():
    return audit_modules.inventory()


def excluded_paths(profile):
    require(profile in ('full', 'photography'), 'Unknown profile')
    if profile == 'full':
        return set()
    return {'CHDK/MODULES/' + m['name'] for m in module_inventory()['modules']
            if not m['photography_included']} | {'CHDK/GAMES/SOKOBAN.LEV'}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read_zip(path):
    with zipfile.ZipFile(path) as archive:
        require(archive.testzip() is None, 'ZIP CRC failure')
        result = {}
        names = set()
        for entry in archive.infolist():
            name = entry.filename
            require(not name.startswith('/') and '\\' not in name
                    and ':' not in name and '..' not in PurePosixPath(name).parts,
                    'Unsafe archive path: ' + name)
            require(name.casefold() not in names, 'Duplicate/case collision: ' + name)
            names.add(name.casefold())
            if not entry.is_dir():
                require(entry.file_size > 0, 'Empty file: ' + name)
                result[name] = archive.read(entry)
        return result


def validate_payload(files, profile='full'):
    excluded = excluded_paths(profile)
    baseline = json.loads((ROOT / 'baseline-output/manifest.json').read_text())
    expected_modules = set()
    for item in baseline:
        if item['path'] == 'main.elf':
            continue
        name = item['path']
        if name.startswith('MODULES/'):
            name = 'CHDK/' + name
            if name in excluded:
                continue
            expected_modules.add(name)
        require(name in files, 'Missing baseline file: ' + name)
        require(len(files[name]) == item['bytes'] and sha(files[name]) == item['sha256'],
                'Current reproducible build mismatch: ' + name)
    require(len(expected_modules) == (38 if profile == 'full' else 30), 'Wrong module count')
    actual_modules = {n for n in files if n.startswith('CHDK/MODULES/')}
    require(actual_modules == expected_modules, 'Unexpected/missing modules')
    require(not (set(files) & excluded), 'Excluded files leaked into profile')
    audit_modules.check_profile(module_inventory(), {PurePosixPath(n).name for n in actual_modules})
    require(not any(n.lower().endswith(('.elf', '.o', '.a', '.fi2', '.fir'))
                    or PurePosixPath(n).name == 'Makefile' for n in files),
            'Build intermediate or firmware-update image in package')
    notes = files.get('camnotes.txt', b'').decode('utf-8', errors='replace')
    require('CHDK for a590 fw:101b' in notes and 'build:1.7.0-6346' in notes,
            'Wrong camera/firmware/revision in upstream metadata')
    # Compare the complete runtime tree with the files actually produced by make.
    runtime = {}
    for path in (ROOT / 'CHDK').rglob('*'):
        name = path.relative_to(ROOT).as_posix()
        if not path.is_file() or path.name == 'Makefile' or '.svn' in name:
            continue
        if path.parent == ROOT / 'CHDK' and path.match('logo*.dat'):
            continue
        if name in excluded:
            continue
        runtime[name] = path.read_bytes()
    if profile == 'photography':
        runtime['CHDK/DATA/PHOTO_UI.TXT'] = b'Enhanced Photography UI: fresh configuration defaults only.\n'
    require({n for n in files if n.startswith('CHDK/')} == set(runtime),
            'Runtime tree membership differs from upstream output')
    for name, content in runtime.items():
        require(files[name] == content, 'Runtime content mismatch: ' + name)
    for directory in ('SCRIPTS', 'LANG', 'FONTS', 'SYMBOLS', 'GRIDS', 'LUALIB',
                      'CURVES', 'DATA', 'BOOKS', 'GAMES', 'HELP'):
        if directory == 'GAMES' and profile == 'photography':
            continue
        require(any(n.startswith('CHDK/' + directory + '/') for n in files),
                'Missing resource directory: ' + directory)
    generated = ['propset%d.lua' % n for n in range(1, 14)]
    generated += ['modelist.lua', 'cnf_core.lua', 'cnf_osd.lua', 'cnf_user.lua', 'cnf_gps.lua']
    for name in generated:
        require('CHDK/LUALIB/GEN/' + name in files, 'Missing generated Lua: ' + name)
    for name in ('readme.txt', 'changelog.txt', 'vers.req', 'CHDK/DATA/logo.dat',
                 'CHDK/SYMBOLS/icon_10.rbf', 'CHDK/SYMBOLS/icon_16.rbf'):
        require(name in files, 'Missing required resource: ' + name)


def verify(path, expected_profile=None):
    files = read_zip(path)
    manifest = json.loads(files.pop('PACKAGE-MANIFEST.json'))
    require(manifest['identity'] == IDENTITY, 'Wrong package identity')
    require(manifest['hardware_tested'] is False, 'Invalid hardware claim')
    profile = manifest['profile']
    excluded_paths(profile)
    if expected_profile is not None:
        require(profile == expected_profile, 'Profile identity mismatch')
    entries = manifest['files']
    require(len(entries) == len({e['path'] for e in entries}), 'Duplicate manifest entries')
    require(set(files) == {e['path'] for e in entries}, 'Manifest membership mismatch')
    for item in entries:
        data = files[item['path']]
        require(len(data) == item['bytes'] and sha(data) == item['sha256'],
                'Manifest mismatch: ' + item['path'])
    for name in ('LICENSES/COPYING', 'LICENSES/ubasic.txt', 'LICENSES/lua.h',
                 'INSTALL/SD_INSTALL_WINDOWS.md', 'INSTALL/SD_ROLLBACK.md',
                 'INSTALL/DISTRIBUTION_PROFILES.md', 'MODULE-INVENTORY.json'):
        require(name in files, 'Missing license/guide: ' + name)
    require(json.loads(files['MODULE-INVENTORY.json']) == module_inventory(), 'Inventory mismatch')
    validate_payload(files, profile)
    # Actually extract and rehash, in addition to checking compressed ZIP CRCs.
    with tempfile.TemporaryDirectory() as tmp:
        with zipfile.ZipFile(path) as archive:
            archive.extractall(tmp)
        for item in entries:
            data = (Path(tmp) / item['path']).read_bytes()
            require(sha(data) == item['sha256'], 'Extraction mismatch: ' + item['path'])
    return manifest


def build(upstream, output, source_commit, profile='full'):
    files = read_zip(upstream)
    validate_payload(files)
    require(set(n for n in files if not n.startswith('CHDK/')) ==
            {'DISKBOOT.BIN', 'readme.txt', 'camnotes.txt', 'changelog.txt', 'vers.req'},
            'Unexpected upstream root contents')
    for target, source in {
        'LICENSES/COPYING': 'COPYING',
        'LICENSES/ubasic.txt': 'doc/6_ubasic_copyright.txt',
        'LICENSES/lua.h': 'lib/lua/lua.h',
        'INSTALL/SD_INSTALL_WINDOWS.md': 'docs/SD_INSTALL_WINDOWS.md',
        'INSTALL/SD_ROLLBACK.md': 'docs/SD_ROLLBACK.md',
        'INSTALL/DISTRIBUTION_PROFILES.md': 'docs/DISTRIBUTION_PROFILES.md',
        'INSTALL/PHOTOGRAPHY_UI.md': 'docs/PHOTOGRAPHY_UI.md',
        'INSTALL/PERFORMANCE_PROFILE.md': 'docs/PERFORMANCE_PROFILE.md',
        'INSTALL/MEMORY_INVESTIGATION.md': 'docs/MEMORY_INVESTIGATION.md',
    }.items():
        files[target] = (ROOT / source).read_bytes()
    for name in excluded_paths(profile):
        require(name in files, 'Expected exclusion absent upstream: ' + name)
        del files[name]
    if profile == 'photography':
        files['CHDK/DATA/PHOTO_UI.TXT'] = b'Enhanced Photography UI: fresh configuration defaults only.\n'
    files['MODULE-INVENTORY.json'] = (json.dumps(module_inventory(), indent=2, sort_keys=True) + '\n').encode()
    manifest = {
        'identity': IDENTITY, 'profile': profile, 'hardware_tested': False,
        'source_commit': source_commit,
        'source_url': 'https://github.com/tglynskyy-hub/chdk-a590is-ua1/tree/' + source_commit,
        'baseline_manifest': 'docs/evidence/baseline-manifest.json',
        'files': [{'path': n, 'bytes': len(b), 'sha256': sha(b)} for n, b in sorted(files.items())],
    }
    files['PACKAGE-MANIFEST.json'] = (json.dumps(manifest, indent=2, sort_keys=True) + '\n').encode()
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, content in sorted(files.items()):
            entry = zipfile.ZipInfo(name, date_time=(2025, 12, 29, 9, 54, 14))
            entry.create_system = 3
            entry.external_attr = 0o100644 << 16
            entry.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(entry, content, compresslevel=9)
    verify(output, profile)
    report = {'archive': output.name, 'bytes': output.stat().st_size,
              'sha256': sha(output.read_bytes()), 'files': len(files),
              'modules': len([n for n in files if n.startswith('CHDK/MODULES/')]), 'profile': profile,
              'identity': IDENTITY, 'source_commit': source_commit, 'hardware_tested': False}
    output.with_suffix('.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    output.with_suffix('.sha256').write_text(report['sha256'] + '  ' + output.name + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('upstream', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('source_commit')
    parser.add_argument('--profile', choices=('full', 'photography'), default='full')
    args = parser.parse_args()
    build(args.upstream, args.output, args.source_commit, args.profile)
