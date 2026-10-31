"""Inventory existing numeric locale entries; does not modify legacy encodings."""
import json
from pathlib import Path
import re

root = Path(__file__).resolve().parents[2]


def entries(name):
    text = (root / "CHDK" / "LANG" / (name + ".lng")).read_bytes().decode("cp1251")
    pairs = re.findall(r'^\s*(\d+)\s+"(.*)"', text, re.MULTILINE)
    ids = [int(key) for key, _ in pairs]
    return {int(key): value for key, value in pairs}, sorted({key for key in ids if ids.count(key) > 1})


english, english_duplicates = entries("english")
ukrainian, ukrainian_duplicates = entries("ukrainian")


def formats(value):
    # Ignore literal %% but retain argument order, widths using *, and length modifiers.
    tokens = re.findall(r'%(?:[-+ #0]*)(?:\d+|\*)?(?:\.(?:\d+|\*))?[hlLjzt]*[diuoxXfFeEgGaAcspn]',
                        value.replace('%%', ''))
    result = []
    for token in tokens:
        result.extend(['int:*'] * token.count('*'))
        result.append(re.search(r'[hlLjzt]*[diuoxXfFeEgGaAcspn]$', token).group())
    return result


codepages = (root / 'lib/font/codepages.h').read_text()
glyphs = (root / 'lib/font/font_8x16_uni.h').read_text()
cp1251 = re.search(r'cp_win_1251\[\].*?\{(.*?)\};', codepages, re.S).group(1)
glyph_checks = [{'codepoint': 'U+%04X' % ord(char), 'covered': ('0x%04X' % ord(char)) in cp1251 and
               bool(re.search(r'\{\s*0x%04X\s*,' % ord(char), glyphs))} for char in 'ҐґЄєІіЇї']
print(json.dumps({
    "method": "numeric .lng lines, cp1251, before port filtering and escape decoding",
    "english_ids": len(english),
    "ukrainian_ids": len(ukrainian),
    "missing_ids": sorted(english.keys() - ukrainian.keys()),
    "extra_ids": sorted(ukrainian.keys() - english.keys()),
    "english_duplicates": english_duplicates,
    "ukrainian_duplicates": ukrainian_duplicates,
    "empty_ukrainian_ids": [key for key, value in ukrainian.items() if not value],
    "ukrainian_string_bytes_upper_bound": sum(len(value.encode("cp1251")) + 1 for value in ukrainian.values()),
    "format_mismatches": [{"id": key, "english": formats(english[key]), "ukrainian": formats(value)}
                          for key, value in ukrainian.items() if key in english and key != 509 and formats(english[key]) != formats(value)],
    "glyph_source_coverage": glyph_checks,
    "width_warning_ids_8px_over_280": [key for key, value in ukrainian.items()
                                     if max(len(line) for line in value.split('\\n')) * 8 > 280],
    "width_method": "Conservative 8px character estimate, not RBF/menu-context layout proof",
    "unchanged_english_ids": [key for key, value in ukrainian.items() if english.get(key) == value],
}, indent=2))
