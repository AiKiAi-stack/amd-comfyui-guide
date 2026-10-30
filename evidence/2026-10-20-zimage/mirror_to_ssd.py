"""Copy pinned trial weights onto the verified non-C NVMe volume."""
import argparse
import hashlib
import json
import shutil
import time
from datetime import datetime,timezone
from pathlib import Path

HERE=Path(__file__).resolve().parent
SSD=Path('G:/AIModels/amd_comfy/zimage-20261020')
parser=argparse.ArgumentParser()
parser.add_argument('--group',choices=['gguf','aio'],required=True)
args=parser.parse_args()
manifest=json.loads((HERE/'download-manifest.json').read_text(encoding='utf-8'))
items=[i for i in manifest if (Path(i['target']).parent.name=='checkpoints')==(args.group=='aio')]
assert shutil.disk_usage('G:/').free > sum(i['bytes'] for i in items)+8*2**30
receipts=[]
for item in items:
    source=Path(item['target'])
    target=SSD/source.parent.name/source.name
    assert target.resolve().is_relative_to(SSD.resolve())
    target.parent.mkdir(parents=True,exist_ok=True)
    start=time.monotonic()
    copied=False
    if not target.exists():
        partial=target.with_name(target.name+'.copy-part')
        copied=True
        transferred=0
        tick=time.monotonic()
        print('COPY',source,'->',target,flush=True)
        with source.open('rb') as src,partial.open('wb') as dst:
            while chunk:=src.read(8*1024*1024):
                dst.write(chunk)
                transferred+=len(chunk)
                if time.monotonic()-tick>15:
                    print('PROGRESS',source.name,transferred,'/',item['bytes'],flush=True)
                    tick=time.monotonic()
        candidate=partial
    else:
        candidate=target
    assert candidate.stat().st_size==item['bytes']
    with candidate.open('rb') as src:
        actual=hashlib.file_digest(src,'sha256').hexdigest()
    assert actual==item['sha256'], f'SSD checksum mismatch: {candidate}'
    if copied: candidate.replace(target)
    receipt={**item,'original_target':item['target'],'ssd_target':str(target),'verified_ssd_sha256':actual,
             'elapsed_seconds':round(time.monotonic()-start,2),'verified_at':datetime.now(timezone.utc).isoformat()}
    (HERE/(source.name+'.ssd-verified.json')).write_text(json.dumps(receipt,indent=2),encoding='utf-8')
    receipts.append(receipt)
    print('SSD_VERIFIED',source.name,receipt['elapsed_seconds'],flush=True)
(HERE/'ssd-model-paths.yaml').write_text('zimage_nvme_trial:\n  base_path: G:/AIModels/amd_comfy/zimage-20261020\n  is_default: true\n  checkpoints: checkpoints\n  diffusion_models: diffusion_models\n  text_encoders: text_encoders\n  vae: vae\n',encoding='utf-8')
print('SSD_GROUP_READY',args.group,flush=True)
