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
}, indent=2))
