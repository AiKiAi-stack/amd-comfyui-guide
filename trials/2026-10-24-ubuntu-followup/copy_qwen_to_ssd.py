"""Restore the verified Qwen subset to Linux SSD without touching source models."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import time

ROOT = Path(__file__).resolve().parents[2]
source_root = ROOT.parent / 'amd_comfy/ComfyUI/models'
target_root = Path('/home/user/.local/share/barely-comfy/models/qwen-20261024')
manifest = [x for x in json.loads((ROOT / 'trials/2026-10-24-ubuntu/nvme-model-hashes.json').read_text())
            if '/repair-20261021/' in x['file']]
needed = sum(x['bytes'] for x in manifest)
if shutil.disk_usage(target_root.parent.parent).free < needed + 15 * 1024**3:
    raise RuntimeError('Need model bytes plus 15GiB free SSD headroom')
records = []
for entry in manifest:
    relative = Path(entry['file'].split('/repair-20261021/', 1)[1])
    source, target = source_root / relative, target_root / relative
    if source.stat().st_size != entry['bytes']:
        raise ValueError('Source size changed: ' + str(relative))
    if target.exists():
        raise FileExistsError('Choose a new destination; preserve ' + str(target))
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_suffix(target.suffix + '.partial')
    digest = hashlib.sha256()
    started = time.monotonic()
    with source.open('rb') as src, partial.open('xb') as dest:
        while data := src.read(16 * 1024**2):
            digest.update(data)
            dest.write(data)
        dest.flush()
        os.fsync(dest.fileno())
    if digest.hexdigest() != entry['sha256']:
        raise ValueError('Source checksum changed; partial retained: ' + str(relative))
    partial.rename(target)
    record = {'file': str(target), 'source': str(source), 'bytes': entry['bytes'],
              'sha256': digest.hexdigest(), 'matches_previous_verified_model': True,
              'seconds': time.monotonic() - started}
    records.append(record)
    (Path(__file__).parent / 'ssd-qwen-copy-progress.json').write_text(json.dumps(records, indent=2) + '\n')
    print('VERIFIED', relative, round(record['seconds'], 1), flush=True)
(Path(__file__).parent / 'ssd-qwen-models.json').write_text(json.dumps(records, indent=2) + '\n')
