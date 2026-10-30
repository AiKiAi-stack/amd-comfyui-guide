"""Read-only inventory of the migrated model files; never copy weights."""
import hashlib
import json
from pathlib import Path
import time

HERE = Path(__file__).resolve().parent
BASE = Path('/media/user/MODELS/AIModels/amd_comfy/comfyui-models-20261024')
files = sorted(p for p in BASE.rglob('*') if p.is_file() and p.suffix in ('.gguf','.safetensors','.ckpt','.pt','.pth'))
records = []
for path in files:
    before = path.stat()
    digest = hashlib.sha256()
    with path.open('rb') as source:
        while block := source.read(8 * 1024**2): digest.update(block)
    after = path.stat()
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        raise RuntimeError('Model changed during read: ' + path.name)
    records.append({'file': path.relative_to(BASE).as_posix(), 'bytes': after.st_size,
                    'sha256': digest.hexdigest(), 'mtime_ns': after.st_mtime_ns})
    (HERE / 'migrated-models.json').write_text(json.dumps({'base':str(BASE),'expected_file_count':len(files),
        'status':'complete' if len(records)==len(files) else 'running','files':records,'time':time.time()},indent=2)+'\n')
    print(len(records), '/', len(files), path.name, flush=True)
