"""Check archived text conditions stayed exact while one initial-latent field changed."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime', type=Path, required=True)
    parser.add_argument('--phase-link', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--changed-latent-field', choices=['samples', 'noise_mask'], default='samples')
    args = parser.parse_args()
    link = json.loads(args.phase_link.read_text(encoding='utf-8'))
    source = link['reused_text_conditions']
    root = (args.runtime / 'ComfyUI/input/repair_conditioning').resolve()

    def checked_path(relative, digest):
        path = (root.parent / relative).resolve()
        if not path.is_relative_to(root) or path.suffix != '.safetensors':
            raise ValueError('Archive must stay inside input/repair_conditioning')
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError('Archive checksum changed')
        return path

    old_path = checked_path(source['archive_file'], source['archive_sha256'])
    new_path = checked_path(link['archive_file'], link['archive_sha256'])
    sys.path.insert(0, str(args.runtime / 'ComfyUI'))
    module_path = Path(__file__).resolve().parents[1] / 'code_source/repair_conditioning/__init__.py'
    spec = importlib.util.spec_from_file_location('verify_repair_archive', module_path)
    archive = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(archive)
    import torch
    old, new = archive.read_archive(old_path), archive.read_archive(new_path)
    counts = {'equal_tensors': 0, 'equal_literals': 0}

    def same(left, right):
        if isinstance(left, torch.Tensor):
            assert isinstance(right, torch.Tensor)
            assert left.dtype == right.dtype and torch.equal(left, right)
            counts['equal_tensors'] += 1
        elif isinstance(left, dict):
            assert isinstance(right, dict) and left.keys() == right.keys()
            for key in left:
                same(left[key], right[key])
        elif isinstance(left, (list, tuple)):
            assert type(left) is type(right) and len(left) == len(right)
            for one, two in zip(left, right):
                same(one, two)
        else:
            assert type(left) is type(right) and left == right
            counts['equal_literals'] += 1

    for name in ('positive', 'negative'):
        same(old[name], new[name])
    assert old['latent'].keys() == new['latent'].keys()
    assert args.changed_latent_field in old['latent'], 'Requested latent field is missing'
    for key in old['latent']:
        if key == args.changed_latent_field:
            assert not torch.equal(old['latent'][key], new['latent'][key]), 'Requested latent field did not change'
        else:
            same(old['latent'][key], new['latent'][key])
    result = {'status': 'pass', 'positive_negative_exact': True,
              'initial_samples_changed': not torch.equal(old['latent']['samples'], new['latent']['samples']),
              'noise_mask_exact': ('noise_mask' not in old['latent'] or
                                  torch.equal(old['latent']['noise_mask'], new['latent']['noise_mask'])),
              'changed_latent_field': args.changed_latent_field, 'other_latent_fields_exact': True,
              **counts, 'source_archive_sha256': source['archive_sha256'],
              'new_archive_sha256': link['archive_sha256']}
    args.out.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
