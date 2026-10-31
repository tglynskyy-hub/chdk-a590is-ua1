"""Cross-profile integrity and negative dependency tests on real build outputs."""
import json
from pathlib import Path
import sys
import tempfile
import zipfile
import package
import audit_modules

root = Path(sys.argv[1])
stem = 'CHDK-A590IS-101B-1.7.0-r6346-enhanced-'
data = {}
reports = {}
for profile in ('full', 'photography'):
    path = root / (stem + profile + '.zip')
    package.verify(path, profile)
    data[profile] = package.read_zip(path)
    reports[profile] = json.loads(path.with_suffix('.json').read_text())
full, photo = data['full'], data['photography']
package.require(set(full) - set(photo) == package.excluded_paths('photography'), 'Wrong profile delta')
package.require(set(photo) - set(full) == {'CHDK/DATA/PHOTO_UI.TXT'}, 'Wrong Photography defaults marker')
for name in photo:
    if name not in ('PACKAGE-MANIFEST.json', 'CHDK/DATA/PHOTO_UI.TXT'):
        package.require(full[name] == photo[name], 'Shared file differs: ' + name)


def reject_package(label, mutate):
    files = dict(photo)
    mutate(files)
    # Update checksums too: negative tests must reach semantic profile checks.
    manifest = json.loads(files.pop('PACKAGE-MANIFEST.json'))
    manifest['files'] = [{'path': n, 'bytes': len(b), 'sha256': package.sha(b)} for n, b in sorted(files.items())]
    files['PACKAGE-MANIFEST.json'] = json.dumps(manifest).encode()
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / 'bad.zip'
        with zipfile.ZipFile(path, 'w') as archive:
            for n, b in files.items():
                archive.writestr(n, b)
        try:
            package.verify(path, 'photography')
        except (ValueError, KeyError):
            print('PASS: rejected ' + label)
        else:
            raise AssertionError('Accepted ' + label)


reject_package('excluded game reintroduced', lambda f: f.update({'CHDK/MODULES/snake.flt': full['CHDK/MODULES/snake.flt']}))
reject_package('missing Lua dependency', lambda f: f.pop('CHDK/MODULES/mdetect.flt'))
reject_package('missing generated resource', lambda f: f.pop('CHDK/LUALIB/GEN/cnf_core.lua'))
reject_package('missing Photography defaults marker', lambda f: f.pop('CHDK/DATA/PHOTO_UI.TXT'))
reject_package('wrong module despite updated checksum', lambda f: f.update({'CHDK/MODULES/lua.flt': f['CHDK/MODULES/lua.flt'] + b'old'}))
reject_package('modified resource with valid checksum', lambda f: f.update({'CHDK/SCRIPTS/interval.lua': b'wrong'}))
inventory = package.module_inventory()
names = {m['name'] for m in inventory['modules'] if m['photography_included']}
try:
    audit_modules.check_profile(inventory, names - {'histo.flt'})
except ValueError:
    print('PASS: dependency closure rejects missing histogram')
else:
    raise AssertionError('Dependency graph accepted missing histogram')
try:
    package.verify(root / (stem + 'full.zip'), 'photography')
except ValueError:
    print('PASS: mislabeled profile rejected')
else:
    raise AssertionError('Accepted Full as Photography')
size_row = (package.ROOT / 'baseline-output/size.txt').read_text().splitlines()[-1].split()
sections = dict(zip(('text', 'data', 'bss'), map(int, size_row[:3])))
baseline_sections = {'text': 88148, 'data': 42212, 'bss': 14004}
delta = {k: sections[k] - baseline_sections[k] for k in sections}
# Review budgets, NOT a measurement of camera free RAM or a safety claim.
for k, budget in {'text': 16384, 'data': 8192, 'bss': 256}.items():
    package.require(delta[k] <= budget, 'Unreviewed section growth: ' + k)
comparison = {
    'profiles': reports,
    'diskboot_identical': full['DISKBOOT.BIN'] == photo['DISKBOOT.BIN'],
    'diskboot_sha256': package.sha(photo['DISKBOOT.BIN']),
    'sections_each_profile': sections, 'section_delta': delta,
    'zip_bytes_saved': reports['full']['bytes'] - reports['photography']['bytes'],
    'payload_bytes_saved': sum(len(full[n]) for n in set(full) - set(photo)),
    'excluded_paths': sorted(set(full) - set(photo)), 'new_hardware_tests': False,
}
(package.ROOT / 'baseline-output/profile-comparison.json').write_text(json.dumps(comparison, indent=2) + '\n')
(package.ROOT / 'baseline-output/module-inventory.json').write_text(json.dumps(inventory, indent=2) + '\n')
print(json.dumps(comparison, indent=2))
print('PASS: both manifests, identical shared payload, exact exclusions, reviewed section budgets and dependency closure')
