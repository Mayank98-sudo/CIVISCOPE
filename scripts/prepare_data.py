"""Restore the included historical government observation snapshots."""
from pathlib import Path
import json
import zipfile
ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / 'data' / 'historical'
TARGET.mkdir(parents=True, exist_ok=True)
with zipfile.ZipFile(ROOT / 'historical-snapshots.zip') as archive:
    for item in archive.infolist():
        name = item.filename
        if Path(name).name != name or not name.startswith('delhi_snapshot_') or not name.endswith('.json'):
            raise ValueError('Unexpected archive member')
        content = archive.read(item)
        json.loads(content)
        target = TARGET / name
        if target.exists() and target.read_bytes() != content:
            raise ValueError(f'Existing snapshot differs: {name}; preserve it and use a clean clone')
        if not target.exists():
            target.write_bytes(content)
    print(f'Restored {len(archive.infolist())} historical snapshots.')
