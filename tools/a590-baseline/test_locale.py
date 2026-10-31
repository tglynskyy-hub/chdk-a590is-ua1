"""Strict CP1251 source checks, format contracts and conservative built-in-font layout."""
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
LINE = re.compile(r'\s*([1-9][0-9]*)\s+"((?:[^"\\]|\\["\\n])*)"\s*(?:(?:#|//).*)?')
FMT = re.compile(r'%(?:[-+ #0]*)(?:\d+|\*)?(?:\.(?:\d+|\*))?(?:hh|ll|[hlLjzt])?[diuoxXfFeEgGaAcspn%]')


def parse(data):
    assert not data.startswith((b'\xef\xbb\xbf', b'\xff\xfe', b'\xfe\xff')), 'BOM'
    text = data.decode('cp1251')
    assert text.encode('cp1251') == data
    result = {}
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith(('#', '//')):
            continue
        m = LINE.fullmatch(line)
        assert m, 'Malformed line/escape: ' + line
        key, value = int(m[1]), m[2]
        assert key not in result, 'Duplicate ID'
        assert value.strip() or (key == 301 and value == ' '), 'Empty translation'
        assert all(ord(c) >= 32 for c in value), 'Control character'
        result[key] = value
    return result


def formats(value):
    result = []
    for m in FMT.finditer(value):
        token = m[0]
        assert token[-1] != 'n', 'Unsafe %n'
        if token == '%%':
            continue
        result.extend(['int:*'] * token.count('*'))
        result.append(re.search(r'(?:hh|ll|[hlLjzt])?[diuoxXfFeEgGaAcsp]$', token)[0])
    return result


def validate(english, ukrainian):
    assert english.keys() == ukrainian.keys(), 'Missing/extra IDs'
    for key, value in ukrainian.items():
        # 509 is a plain menu label "battery % level", never a printf format.
        # The % le substring otherwise resembles a floating-point specifier.
        if key != 509:
            assert formats(english[key]) == formats(value), 'Format contract ID ' + str(key)
        assert max(map(len, value.split('\\n'))) <= 35, 'Width ID ' + str(key)
        assert len(value.split('\\n')) <= 8, 'Message height ID ' + str(key)
    size = sum(len(v.encode('cp1251')) + 1 for v in ukrainian.values())
    assert size < 32766, '15-bit language offsets overflow'
    assert formats(ukrainian[107]) == ['s'] * 8
    assert formats(ukrainian[109]) == ['d', 'd', 'X']
    # gui_menu.c allocates seven built-in glyphs to enum values.
    for key in range(712, 744):
        assert len(ukrainian[key]) <= 7, 'Enum width ID ' + str(key)
    # Actual GUI build-info/memory sprintf consumers use a 256-byte buffer.
    build = ukrainian[107].replace('\\n', '\n') % ('1.7.0', 'r6346', '6346', 'Dec 29 2025', '09:54:14', 'a590', '101b', '8.3.1')
    memory = ukrainian[109].replace('\\n', '\n') % (2147483647, 2147483647, 0xffffffff)
    assert len(build.encode('cp1251')) < 256 and len(memory.encode('cp1251')) < 256
    assert max(map(len, build.splitlines())) <= 35
    assert max(map(len, memory.splitlines())) <= 35
    cp = (ROOT / 'lib/font/codepages.h').read_text()
    cp = re.search(r'cp_win_1251\[\].*?\{(.*?)\};', cp, re.S)[1]
    glyphs = (ROOT / 'lib/font/font_8x16_uni.h').read_text()
    for char in set(''.join(ukrainian.values())) | set('ҐґЄєІіЇї'):
        if ord(char) >= 128:
            assert '0x%04X' % ord(char) in cp, 'Codepage glyph ' + char
            assert re.search(r'\{\s*0x%04X\s*,' % ord(char), glyphs), 'Font glyph ' + char
    # Detect accidental UTF-8-as-CP1251, including common mojibake characters.
    assert not any(c in ''.join(ukrainian.values()) for c in 'ЂЃљњќћџЎў')
    return {'ids': len(ukrainian), 'language_buffer_upper_bound': size,
            'offset_table_bytes': (max(english) + 1) * 2,
            'temporary_pointer_table_bytes_arm': (max(english) + 1) * 4,
            'width': '35 columns at 8px; actual camera/RBF rendering still requires hardware test',
            'build_info_bytes': len(build.encode('cp1251')), 'memory_info_bytes': len(memory.encode('cp1251'))}


def main():
    english = parse((ROOT / 'CHDK/LANG/english.lng').read_bytes())
    raw = (ROOT / 'CHDK/LANG/ukrainian.lng').read_bytes()
    ukrainian = parse(raw)
    report = validate(english, ukrainian)
    for label, data in [('duplicate', raw + b'1 "bad"\n'), ('bad escape', b'1 "bad\\t"'),
                        ('BOM', b'\xef\xbb\xbf' + raw), ('empty', b'1 ""')]:
        try:
            parse(data)
        except (AssertionError, UnicodeError):
            pass
        else:
            raise AssertionError('Accepted ' + label)
    for label, change in [('missing', lambda d: d.pop(1)), ('type', lambda d: d.update({107: '%d'})),
                          ('count', lambda d: d.update({109: '%d %X'})), ('write', lambda d: d.update({109: '%n'})),
                          ('width', lambda d: d.update({1: 'a' * 36})), ('UTF8', lambda d: d.update(parse(raw.decode('cp1251').encode('utf-8'))))]:
        try:
            bad = dict(ukrainian)
            change(bad)
            validate(english, bad)
        except (AssertionError, UnicodeError):
            pass
        else:
            raise AssertionError('Accepted ' + label)
    assert formats('%*.*ld %% %s') == ['int:*', 'int:*', 'ld', 's']
    (ROOT / 'baseline-output').mkdir(exist_ok=True)
    (ROOT / 'baseline-output/locale-tests.json').write_text(json.dumps(report, indent=2) + '\n')
    print('PASS: localization, encoding, glyphs, formats, bounds and 10 negative fixtures')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
