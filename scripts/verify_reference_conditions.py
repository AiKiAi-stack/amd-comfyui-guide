"""Verify real precomputed Qwen references survived text encoding bit-exactly."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from safetensors import safe_open


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime', type=Path, required=True)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--label', required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    reference = json.loads((args.run / 'reference-link.json').read_text(encoding='utf-8'))
    if 'archive_file' not in reference:
        reference = reference[args.label]
    phase = json.loads((args.run / 'phases/graphs' / args.label / 'phase-link.json').read_text(encoding='utf-8'))
    root = (args.runtime / 'ComfyUI/input/repair_conditioning').resolve()

    def read(record):
        path = (root.parent / record['archive_file']).resolve()
        if not path.is_relative_to(root) or hashlib.sha256(path.read_bytes()).hexdigest() != record['archive_sha256']:
            raise ValueError('Reference/conditioning archive path or SHA changed')
        with safe_open(str(path), framework='numpy') as reader:
            meta = reader.metadata()
            if meta.get('repair_conditioning_version') != '1':
                raise ValueError('Unknown archive version')

            def unpack(value):
                kind, item = value
                if kind == 'tensor':
                    return reader.get_tensor(item).copy()
                if kind == 'dict':
                    return {unpack(k): unpack(v) for k, v in item}
                if kind in {'list', 'tuple'}:
                    result = [unpack(v) for v in item]
                    return tuple(result) if kind == 'tuple' else result
                if kind == 'literal':
                    return item
                raise ValueError('Unknown archive node')
            return unpack(json.loads(meta['tree']))

    original, encoded = read(reference), read(phase)
    reference_count = len(original['reference_latents'])
    checked = 0
    for branch in ('positive', 'negative'):
        assert encoded[branch]
        for _, metadata in encoded[branch]:
            actual = metadata['reference_latents']
            assert len(actual) == reference_count
            for expected, output in zip(original['reference_latents'], actual):
                assert expected.dtype == output.dtype and np.array_equal(expected, output)
                checked += 1
    expected_initial, actual_initial = original['initial_latent'], encoded['latent']
    assert expected_initial.keys() == actual_initial.keys()
    for key in expected_initial:
        expected, output = expected_initial[key], actual_initial[key]
        assert expected.dtype == output.dtype and np.array_equal(expected, output)
    result = {'status': 'pass', 'reference_count': reference_count,
              'positive_negative_reference_tensors_checked': checked,
              'reference_latents_exact': True, 'initial_samples_and_mask_exact': True,
              'reference_archive_sha256': reference['archive_sha256'],
              'conditioning_archive_sha256': phase['archive_sha256']}
    args.out.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
