"""Bounded real NTFS GGUF tensor transfer probe; run each mode in a child."""
import argparse
import hashlib
import json
from pathlib import Path
import time

import gguf
import torch

parser = argparse.ArgumentParser()
parser.add_argument('mode', choices=['mmap', 'cpu-copy'])
parser.add_argument('--out', type=Path, required=True)
args = parser.parse_args()
path = Path('/media/user/MODELS/AIModels/amd_comfy/comfyui-models-20261024/diffusion_models/kroma-v0.3.1-turbo-opd-Q2_K.gguf')
reader = gguf.GGUFReader(str(path))
tensor = max((t for t in reader.tensors if t.data.nbytes <= 16*1024**2), key=lambda t:t.data.nbytes)
raw = torch.from_numpy(tensor.data)
expected = hashlib.sha256(raw.numpy().tobytes()).hexdigest()
if args.mode == 'cpu-copy': raw = raw.clone()
record = {'mode': args.mode, 'source': str(path), 'tensor': tensor.name, 'bytes': tensor.data.nbytes,
          'expected_sha256': expected, 'status': 'before_cuda_copy'}
args.out.write_text(json.dumps(record, indent=2)+'\n')
start = time.monotonic()
gpu = raw.to('cuda');torch.cuda.synchronize()
restored = gpu.to('cpu')
record.update(status='pass', seconds=time.monotonic()-start, actual_sha256=hashlib.sha256(restored.numpy().tobytes()).hexdigest())
assert record['actual_sha256']==expected
args.out.write_text(json.dumps(record, indent=2)+'\n')
print(record)
