"""Conservative source dependency inventory for the pinned 38-module baseline.

Includes conditional library calls (over-approximation), not a complete C call graph.
Only reviewed independent simple modules are eligible for package exclusion.
"""
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
# name | category | primary source | purpose / reason for retaining
ROWS = '''
4wins|nonessential|games/gui_4wins|Connect-four game
_confmig|mandatory|conf_migrate|Old configuration and script config-ID migration
_dng|mandatory|dng|DNG creation, metadata, bad pixels, conversion
_hexbox|mandatory|gui_hexbox|Hexadecimal input used by classic configuration/debug UI
_osd_le|mandatory|gui_osd_edit|OSD layout editor and histogram preview
_rawop|photography|raw_merge|File-based RAW merge/subtract; distinct from Lua rawop API
_tbox|mandatory|gui_tbox|Text input for file browser, Lua and Eye-Fi
benchm|developer|gui_bench|CPU/memory/file benchmark; retained for measurements
calend|nonessential|gui_calendar|Standalone calendar, no photography service
cpuinfo|developer|cpuinfo|CPU diagnostic; retained for investigation
curves|photography|curves|10-bit RAW tone curves; also exposed to scripts
edgeovr|photography|edgeoverlay|Edge overlay for composition/alignment
exmemins|developer|exmem_inspector|Inspect EXMEM; retaining does not enable EXMEM
eyefi|uncertain|eyefi|Eye-Fi card control; card compatibility not tested, retain
fselect|mandatory|gui_fselect|File selector/browser and RAW file operations
fshelter|developer|file_shelter|File backup/restore diagnostic utility; retain pending workflow tests
fwcrc|developer|firmware_crc|Firmware CRC diagnostic, not boot compatibility check
grids|photography|gui_grid|Composition grids
histo|mandatory|histogram|Live histogram plus Zebra/OSD editor support
lua|mandatory|luascript|Lua VM, shooting hooks and rawhookops
mastmind|nonessential|games/gui_mastermind|Mastermind game
mdetect|photography|motion_detector|Motion detection used by Lua and uBASIC
memview|developer|gui_debug|Memory viewer; retain for classic tools compatibility
modinsp|developer|module_inspector|Module inspector with explicit core menu reference
mpopup|mandatory|gui_mpopup|Popup UI for file browser, user editor and Eye-Fi
palette|mandatory|gui_palette|Color selection and palette UI
rawevhst|photography|raw_ev_histo|RAW EV histogram after capture
reversi|nonessential|games/gui_reversi|Reversi game
scrdump|developer|scrdump|Display dump diagnostic; useful for UI QA
shothist|photography|shot_histogram|Shot histogram and script range metering
snake|nonessential|games/gui_snake|Snake game
sokoban|nonessential|games/gui_sokoban|Sokoban game with external level data
sudoku|nonessential|games/gui_sudoku|Sudoku game
tetris|nonessential|games/gui_tetris|Tetris game
txtread|mandatory|gui_read|Text viewer used by file browser and classic Reader UI
ubasic|mandatory|ubasic|Retained for existing .bas scripts and compatibility
useredit|mandatory|user_menu_edit|Quick/user-menu editor and script/module shortcuts
zebra|mandatory|zebra|Live highlight warning with optional histogram
'''
LIBS = dict(zip(
    'libconfmigrate libdng libhexbox librawop libtextbox libedgeovr libfselect libcurves libgrids libhisto libmotiondetect libmpopup libpalette librawevhisto libshothisto libtxtread libzebra'.split(),
    '_confmig _dng _hexbox _rawop _tbox edgeovr fselect curves grids histo mdetect mpopup palette rawevhst shothist txtread zebra'.split()))
LIBS['libscriptapi'] = 'lua ubasic'
SUPPORT = {
    'lua': ['modules/script_key_funcs.c', 'modules/script_shoot_hook.c', 'modules/rawhookops.c', 'modules/dbg_dump.c', 'modules/cordic_math.c'],
    'ubasic': ['modules/script_key_funcs.c', 'lib/ubasic/ubasic.c'],
    'edgeovr': ['modules/bitvector.c'], 'eyefi': ['modules/md5.c', 'modules/sha1.c'],
}


def stripped(text):
    return re.sub(r'/\*.*?\*/|//[^\n]*', '', text, flags=re.S)


def inventory():
    baseline = json.loads((ROOT / 'docs/evidence/baseline-manifest.json').read_text())
    hashes = {Path(e['path']).name: e for e in baseline if e['path'].startswith('MODULES/')}
    records = []
    cfiles = sorted(p for d in ('core', 'modules', 'lib') for p in (ROOT / d).rglob('*.c'))
    for row in ROWS.strip().splitlines():
        name, category, source, purpose = row.split('|')
        sources = ['modules/' + source + '.c'] + SUPPORT.get(name, [])
        if source.startswith('games/'):
            sources.append('modules/games/simple_game.c')
        text = '\n'.join(stripped((ROOT / s).read_text(errors='replace')) for s in sources)
        dependencies = set()
        for lib in re.findall(r'\b(lib\w+)\s*->', text):
            if lib not in LIBS:
                raise ValueError('Unmapped library ' + lib + ' in ' + name)
            dependencies.update(n + '.flt' for n in LIBS[lib].split())
        references = []
        aliases = [k for k, v in LIBS.items() if name in v.split()]
        for path in cfiles:
            if path.relative_to(ROOT).as_posix() in sources:
                continue
            for number, line in enumerate(path.read_text(errors='replace').splitlines(), 1):
                if ('"' + name + '.flt"') in line or any(re.search(r'\b' + lib + r'\s*->', line) for lib in aliases):
                    references.append(path.relative_to(ROOT).as_posix() + ':' + str(number))
        removable = category == 'nonessential'
        # Fail closed if a reviewed standalone leaf acquires a static consumer.
        if removable and (dependencies or references):
            raise ValueError('Excluded leaf acquired dependencies/references: ' + name)
        records.append({
            'name': name + '.flt', 'category': category, 'purpose': purpose,
            'sources': sources, 'static_consumers': references,
            'direct_dependencies': sorted(dependencies),
            'a590_use': 'User-invoked standalone tool/game' if removable else 'Available via core/UI/script on demand; conditional calls included',
            'essential_to_photography': category == 'mandatory',
            'photography_included': not removable,
            'exclusion_safety': 'Reviewed standalone leaf; no core service dependency' if removable else 'Retain: compatibility or untested feature dependency',
            'gui_after_exclusion': 'Dynamic entry absent; Games/Tools parent remains. Cached menu needs restart after card changes.' if removable else 'Not excluded; existing GUI preserved',
            'script_impact': 'No ordinary photography API removed; saved user-menu module shortcut will fail and must be removed.' if removable else 'Existing script APIs preserved by retaining module and dependencies',
            'resident_ram_saved_bytes': 0,
            'ram_note': 'SD exclusion does not shrink core. On-demand code/BSS only allocated when loaded; dynamic menu metadata can differ.',
            'baseline_bytes': hashes[name + '.flt']['bytes'], 'baseline_sha256': hashes[name + '.flt']['sha256'],
        })
    by_name = {r['name']: r for r in records}
    if set(by_name) != set(hashes):
        raise ValueError('Inventory does not cover exact baseline')
    for r in records:
        pending = list(r['direct_dependencies'])
        seen = set()
        while pending:
            dep = pending.pop()
            if dep not in seen:
                seen.add(dep)
                pending.extend(by_name[dep]['direct_dependencies'])
        r['transitive_dependencies'] = sorted(seen - {r['name']})
        r['required_by_modules'] = [x['name'] for x in records if r['name'] in x['direct_dependencies']]
    result = {'schema': 1, 'method': 'Reviewed sources + conservative lib-pointer edges and core consumers; not complete binary call graph',
              'limitations': 'Conditional paths over-approximated. Dynamically constructed native module calls and external saved shortcuts cannot be proven absent. No hardware validation implied.',
              'modules': records}
    check_profile(result, {r['name'] for r in records if r['photography_included']})
    return result


def check_profile(data, names):
    by_name = {m['name']: m for m in data['modules']}
    for name in names:
        missing = set(by_name[name]['transitive_dependencies']) - names
        if missing:
            raise ValueError(name + ' missing dependencies: ' + ', '.join(sorted(missing)))
    for record in data['modules']:
        if record['photography_included'] and record['name'] not in names:
            raise ValueError('Required compatibility module absent: ' + record['name'])


if __name__ == '__main__':
    print(json.dumps(inventory(), indent=2))
