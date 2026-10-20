"""Mirror existing pinned Klein weights to G: NVMe, verifying SHA-256."""
import hashlib
import json
import shutil
import time
from datetime import datetime,timezone
from pathlib import Path

HERE=Path(__file__).resolve().parent
SSD=Path('G:/AIModels/amd_comfy/flux2-klein-20261020')
manifest=json.loads((HERE/'download-manifest.json').read_text(encoding='utf-8'))
assert shutil.disk_usage('G:/').free>sum(i['bytes'] for i in manifest)+8*2**30
for item in manifest:
    source=Path(item['target'])
    receipt=source.with_name(source.name+'.verified.json')
    assert source.stat().st_size==item['bytes']
    target=SSD/source.parent.name/source.name
    assert target.resolve().is_relative_to(SSD.resolve())
    target.parent.mkdir(parents=True,exist_ok=True)
    started=time.monotonic()
    fresh=not target.exists()
    candidate=target.with_name(target.name+'.copy-part') if fresh else target
    if fresh:
        print('COPY',source,'->',target,flush=True)
        copied=0
        tick=time.monotonic()
        with source.open('rb') as src,candidate.open('wb') as dst:
            while chunk:=src.read(8*1024*1024):
                dst.write(chunk)
                copied+=len(chunk)
                if time.monotonic()-tick>15:
                    print('PROGRESS',source.name,copied,'/',item['bytes'],flush=True)
                    tick=time.monotonic()
    assert candidate.stat().st_size==item['bytes']
    with candidate.open('rb') as stream:
        actual=hashlib.file_digest(stream,'sha256').hexdigest()
    assert actual==item['sha256'],f'Wrong SSD checksum: {candidate}'
    if fresh: candidate.replace(target)
    verified=dict(item,ssd_target=str(target),verified_ssd_sha256=actual,verified_at=datetime.now(timezone.utc).isoformat(),elapsed_seconds=round(time.monotonic()-started,2))
    (HERE/(source.name+'.ssd-verified.json')).write_text(json.dumps(verified,indent=2),encoding='utf-8')
    print('SSD_VERIFIED',source.name,verified['elapsed_seconds'],flush=True)
(HERE/'ssd-model-paths.yaml').write_text('flux2_klein_nvme_trial:\n  base_path: G:/AIModels/amd_comfy/flux2-klein-20261020\n  is_default: true\n  diffusion_models: diffusion_models\n  text_encoders: text_encoders\n  vae: vae\n',encoding='utf-8')
print('FLUX_SSD_READY',flush=True)
