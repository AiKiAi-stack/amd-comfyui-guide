"""Start a scoped, GPU-probed Klein service with verified G: weight mirrors."""
import argparse
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
parser=argparse.ArgumentParser()
parser.add_argument('--pinned-memory',action='store_true')
args=parser.parse_args()
manifest=json.loads((HERE/'download-manifest.json').read_text(encoding='utf-8'))
for item in manifest:
    receipt=json.loads((HERE/(Path(item['target']).name+'.ssd-verified.json')).read_text(encoding='utf-8'))
    assert receipt['verified_ssd_sha256']==item['sha256']
    assert Path(receipt['ssd_target']).stat().st_size==item['bytes']
subprocess.run([sys.executable,'-X','utf8','-u',str(HERE/'probe_gpu.py')],cwd=ROOT,check=True)
probe=json.loads(sorted((HERE/'gpu-probes').glob('*/result.json'))[-1].read_text(encoding='utf-8'))
assert probe['healthy'], 'No inference or reset after an unhealthy probe'
spec=importlib.util.spec_from_file_location('owned_server_manager',ROOT/'trials/2026-10-19-features/manage_server.py')
manager=importlib.util.module_from_spec(spec)
spec.loader.exec_module(manager)
manager.restart('flux2-klein-nvme-pinned' if args.pinned_memory else 'flux2-klein-nvme',cpu_text=False,fast_disk=True,
    extra_args=['--enable-dynamic-vram','--reserve-vram','2.0',
                '--fp8_e4m3fn-text-enc','--extra-model-paths-config',str(HERE/'ssd-model-paths.yaml')]
                +([] if args.pinned_memory else ['--disable-pinned-memory']))
