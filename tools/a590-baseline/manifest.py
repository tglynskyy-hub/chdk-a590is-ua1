"""Record actual artifact sizes/hashes; fail if the camera binary is absent."""
import hashlib
import json
from pathlib import Path
import sys

root = Path(sys.argv[1])
binary = root / "DISKBOOT.BIN"
if not binary.is_file() or not binary.stat().st_size:
    raise SystemExit("Missing or empty DISKBOOT.BIN")
files = [binary, root / "main.elf", *sorted((root / "MODULES").glob("*.flt"))]
if len(files) <= 2:
    raise SystemExit("No modules generated")
records = []
for path in files:
    data = path.read_bytes()
    records.append({"path": path.relative_to(root).as_posix(), "bytes": len(data),
                    "sha256": hashlib.sha256(data).hexdigest()})
(root / "manifest.json").write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")
print(json.dumps(records[:2], indent=2))
print(f"Verified {len(records) - 2} module artifacts")

# Track changes without inventing a hardware-safe growth threshold.
reference = Path(__file__).resolve().parents[2] / "docs/evidence/baseline-manifest.json"
if reference.exists():
    baseline = {item["path"]: item for item in json.loads(reference.read_text(encoding="utf-8-sig"))}
    current = {item["path"]: item for item in records}
    changes = []
    for name in sorted(baseline.keys() | current.keys()):
        old, new = baseline.get(name), current.get(name)
        if old != new:
            changes.append({"path": name, "previous_bytes": old["bytes"] if old else None,
                            "current_bytes": new["bytes"] if new else None,
                            "delta_bytes": new["bytes"] - old["bytes"] if old and new else None})
    (root / "size-changes.json").write_text(json.dumps(changes, indent=2) + "\n", encoding="utf-8")
    print(f"Artifacts changed relative to recorded baseline: {len(changes)}")
