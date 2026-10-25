"""Verify the installed Qwen node's optional VAE contract and conservative pruning."""
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

spec = importlib.util.spec_from_file_location('qwen_phase_runner',
    Path(__file__).resolve().parents[1] / 'trials/2026-10-24-ubuntu/run_qwen_phases.py')
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class NoReferenceClip:
    def tokenize(self, prompt, **kwargs):
        assert kwargs['keep_vision'] is True and not kwargs['images']
        return prompt

    def encode_from_tokens_scheduled(self, tokens):
        return [[torch.full((1, 2, 3), float(len(tokens))), {'prompt': tokens}]]


class ForbiddenVae:
    def encode(self, image):
        raise AssertionError('Reference encoding requires a real VAE')


class NoReferenceVaeTests(unittest.TestCase):
    def test_real_core_conditions_and_latent_equal_with_unused_vae_omitted(self):
        with_vae = TextEncodeQwenImage21.execute(NoReferenceClip(), 'blue ghost', '',
            vae=ForbiddenVae(), resolution=512).result
        without = TextEncodeQwenImage21.execute(NoReferenceClip(), 'blue ghost', '',
            resolution=512).result
        for first, second in zip(with_vae[:2], without[:2]):
            torch.testing.assert_close(first[0][0], second[0][0], rtol=0, atol=0)
            self.assertEqual(first[0][1], second[0][1])
        torch.testing.assert_close(with_vae[2]['samples'], without[2]['samples'], rtol=0, atol=0)
        self.assertEqual(tuple(without[2]['samples'].shape), (1, 64, 32, 32))

    def test_reference_and_unknown_inputs_keep_vae_dependency(self):
        base = {'class_type': 'TextEncodeQwenImage21', 'inputs': {
            'clip': ['2', 0], 'vae': ['3', 0], 'prompt': 'ghost', 'negative_prompt': '', 'resolution': 512}}
        graph = {'4': base}
        self.assertNotIn('vae', runner.omit_unused_vae(graph)['4']['inputs'])
        self.assertIn('vae', graph['4']['inputs'])
        for name in ('image_1', 'images', 'future_option'):
            changed = {'4': {'class_type': base['class_type'], 'inputs': {**base['inputs'], name: ['9', 0]}}}
            self.assertIn('vae', runner.omit_unused_vae(changed)['4']['inputs'])
        with self.assertRaisesRegex(AssertionError, 'real VAE'):
            TextEncodeQwenImage21.execute(NoReferenceClip(), 'ghost', '', vae=ForbiddenVae(),
                resolution=64, images={'image_1': torch.ones(1, 64, 64, 3)})


if __name__ == '__main__':
    unittest.main(argv=[sys.argv[0]])
