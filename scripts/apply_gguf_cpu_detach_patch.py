"""Replace GGUF's CUDA round trip for CPU mmap detachment, retaining a source backup."""
import argparse
import hashlib
import json
from pathlib import Path

IMPORT = b'from .ops import GGMLOps, move_patch_to_device'
PIN = b'self.named_modules_to_munmap[op_key].to(self.load_device).to(self.offload_device)'
TAIL = b'                    m.to(self.load_device).to(self.offload_device)'
MARKER = b'def _detach_mmap_module('
HELPER = '''def _detach_mmap_module(module, load_device, offload_device):
    if torch.device(load_device).type != "cuda" or torch.device(offload_device).type != "cpu":
        return module.to(load_device).to(offload_device)

    def copy_to_cpu(tensor):
        if isinstance(tensor, GGMLTensor):
            base = tensor.as_subclass(torch.Tensor).to(device="cpu", copy=True)
            return GGMLTensor(base, tensor_type=tensor.tensor_type,
                              tensor_shape=tensor.tensor_shape, patches=tensor.patches.copy())
        return tensor.to(device="cpu", copy=True)

    with torch.no_grad():
        return module._apply(copy_to_cpu)


'''


def patch_bytes(source):
    if MARKER in source:
        if source.count(MARKER) == 1 and PIN not in source and TAIL not in source:
            return source
        raise ValueError('Ambiguous existing GGUF CPU detach patch')
    for needle in (IMPORT, PIN, TAIL, b'class GGUFModelPatcher('):
        if source.count(needle) != 1:
            raise ValueError('Unrecognized GGUF source; refusing to patch')
    newline = b'\r\n' if b'\r\n' in source else b'\n'
    helper = HELPER.encode().replace(b'\n', newline)
    return (source.replace(IMPORT, IMPORT + b', GGMLTensor', 1)
            .replace(b'class GGUFModelPatcher(', helper + b'class GGUFModelPatcher(', 1)
            .replace(PIN, b'_detach_mmap_module(self.named_modules_to_munmap[op_key], self.load_device, self.offload_device)', 1)
            .replace(TAIL, b'                    _detach_mmap_module(m, self.load_device, self.offload_device)', 1))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plugin', type=Path, required=True)
    parser.add_argument('--record', type=Path, required=True)
    args = parser.parse_args()
    target = args.plugin.resolve() / 'nodes.py'
    before = target.read_bytes()
    after = patch_bytes(before)
    compile(after, str(target), 'exec')
    if after == before:
        print('Already applied; existing evidence preserved')
        return
    backup = args.record.with_suffix('.original.py')
    if args.record.exists() or backup.exists():
        raise FileExistsError('Preserve prior evidence; select a fresh patch record')
    args.record.parent.mkdir(parents=True, exist_ok=True)
    backup.write_bytes(before)
    target.write_bytes(after)
    args.record.write_text(json.dumps({'file': str(target), 'before_sha256': hashlib.sha256(before).hexdigest(),
        'after_sha256': hashlib.sha256(after).hexdigest(), 'scope': 'CUDA load / CPU offload mmap detachment only; not unpatch/OOM recovery'}, indent=2) + '\n')
    print('Applied CPU mmap detach patch')


if __name__ == '__main__':
    main()
