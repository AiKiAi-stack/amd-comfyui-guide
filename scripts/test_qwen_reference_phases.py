"""Compare cached reference encoding against the installed Qwen 2.1 node."""
import argparse
import importlib.util
from pathlib import Path
import sys
import unittest

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--runtime', type=Path, required=True)
args = parser.parse_args()
sys.path.insert(0, str(args.runtime / 'ComfyUI'))
sys.argv = [sys.argv[0], '--cpu']
import comfy.options
comfy.options.enable_args_parsing()
import torch
from comfy_extras.nodes_qwen import TextEncodeQwenImage21

module_path = Path(__file__).resolve().parents[1] / 'code_source/repair_conditioning/__init__.py'
spec = importlib.util.spec_from_file_location('reference_phase_test', module_path)
repair = importlib.util.module_from_spec(spec)
spec.loader.exec_module(repair)


class ObservableClip:
    def tokenize(self, prompt, **kwargs):
        return {'prompt': prompt, **kwargs}

    def encode_from_tokens_scheduled(self, tokens):
        assert tokens['keep_vision'] is False
        embedding = torch.tensor([[[len(tokens['prompt'])]]], dtype=torch.float32)
        return [[embedding, {'image_sums': [image.sum() for image in tokens['images']]}]]


class ObservableVae:
    def encode(self, image):
        return torch.nn.functional.avg_pool2d(image[..., :3].movedim(-1, 1), 16)


class ReferencePhaseTests(unittest.TestCase):
    def same(self, left, right):
        if isinstance(left, torch.Tensor):
            self.assertEqual(left.dtype, right.dtype)
            torch.testing.assert_close(left, right, rtol=0, atol=0)
        elif isinstance(left, dict):
            self.assertEqual(left.keys(), right.keys())
            for key in left:
                self.same(left[key], right[key])
        elif isinstance(left, (list, tuple)):
            self.assertEqual(type(left), type(right))
            self.assertEqual(len(left), len(right))
            for one, two in zip(left, right):
                self.same(one, two)
        else:
            self.assertEqual(left, right)

    def test_non_square_rgba_and_multiple_references_match_core(self):
        torch.manual_seed(8)
        images = {'image_1': torch.rand(1, 96, 160, 4), 'image_2': torch.rand(1, 128, 96, 3)}
        expected = TextEncodeQwenImage21.execute(ObservableClip(), 'fox', 'cat',
            vae=ObservableVae(), resolution=128, images=images).result
        payload = repair.qwen_reference_payload(ObservableVae(), images, 128)
        actual = repair.encode_qwen_reference_payload(ObservableClip(), 'fox', 'cat', payload)
        self.same(expected, actual)

    def test_independent_initial_latent_and_mask_are_preserved(self):
        images = {'image_1': torch.rand(1, 64, 64, 3)}
        initial = {'samples': torch.ones(1, 64, 4, 4), 'noise_mask': torch.rand(1, 64, 64)}
        payload = repair.qwen_reference_payload(ObservableVae(), images, 64, initial)
        actual = repair.encode_qwen_reference_payload(ObservableClip(), 'fox', 'cat', payload)
        self.same(actual[2], initial)

    def test_corrupt_or_mismatched_payload_is_rejected(self):
        with self.assertRaises(ValueError):
            repair.encode_qwen_reference_payload(ObservableClip(), 'fox', 'cat', {'kind': 'unknown'})
        payload = repair.qwen_reference_payload(ObservableVae(), {'image_1': torch.rand(1, 64, 64, 3)}, 64)
        payload['reference_latents'] = []
        with self.assertRaises(ValueError):
            repair.encode_qwen_reference_payload(ObservableClip(), 'fox', 'cat', payload)


unittest.main(argv=['test_qwen_reference_phases'])
