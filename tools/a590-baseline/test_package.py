"""Negative checks against a real distribution; run after upstream compilation."""
import json
from pathlib import Path
import sys
import tempfile
import zipfile
import package

original = package.read_zip(Path(sys.argv[1]))


def rejected(label, mutate):
    files = dict(original)
    mutate(files)
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / 'bad.zip'
        with zipfile.ZipFile(path, 'w') as archive:
            for name, data in files.items():
                archive.writestr(name, data)
        try:
            package.verify(path)
        except (ValueError, KeyError):
            print('PASS: rejected ' + label)
        else:
            raise AssertionError('Accepted ' + label)


def rehash_changed_binary(files):
    files['DISKBOOT.BIN'] += b'corrupt'
    manifest = json.loads(files['PACKAGE-MANIFEST.json'])
    for entry in manifest['files']:
        if entry['path'] == 'DISKBOOT.BIN':
            entry.update(bytes=len(files['DISKBOOT.BIN']), sha256=package.sha(files['DISKBOOT.BIN']))
    files['PACKAGE-MANIFEST.json'] = json.dumps(manifest).encode()


rejected('missing module', lambda f: f.pop('CHDK/MODULES/4wins.flt'))
rejected('empty resource', lambda f: f.update({'CHDK/DATA/logo.dat': b''}))
rejected('missing license', lambda f: f.pop('LICENSES/COPYING'))
rejected('path traversal', lambda f: f.update({'../escape': b'x'}))
rejected('wrong binary despite updated manifest', rehash_changed_binary)
rejected('case collision', lambda f: f.update({'diskboot.bin': f['DISKBOOT.BIN']}))
rejected('extra firmware image', lambda f: f.update({'main.elf': b'x'}))
