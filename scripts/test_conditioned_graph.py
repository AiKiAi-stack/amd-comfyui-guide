"""Check that phase splitting preserves actual sampling and output dependencies."""
import copy
from pathlib import Path
import unittest

from run_conditioned_repair import prune


class GraphTests(unittest.TestCase):
    def test_sampling_keeps_model_and_composite_but_removes_encoder(self):
        graph = {
            "clip": {"class_type": "CLIPLoader", "inputs": {}},
            "text": {"class_type": "Encode", "inputs": {"clip": ["clip", 0]}},
            "image": {"class_type": "LoadImage", "inputs": {}},
            "latent": {"class_type": "VAEEncode", "inputs": {"image": ["image", 0]}},
            "model": {"class_type": "UnetLoaderGGUF", "inputs": {}},
            "sampler": {"class_type": "KSampler", "inputs": {
                "positive": ["text", 0], "negative": ["text", 1], "latent_image": ["latent", 0],
                "model": ["model", 0], "seed": 123, "steps": 15, "denoise": 0.85}},
            "composite": {"class_type": "Composite", "inputs": {
                "source": ["sampler", 0], "destination": ["image", 0]}},
            "save": {"class_type": "SaveImage", "inputs": {"images": ["composite", 0]}}}
        original = copy.deepcopy(graph)
        graph["load"] = {"class_type": "LoadRepairConditioning", "inputs": {}}
        for name, slot in (("positive", 0), ("negative", 1), ("latent_image", 2)):
            graph["sampler"]["inputs"][name] = ["load", slot]
        phase = prune(graph, ["save"])
        self.assertEqual(set(phase), {"image", "model", "sampler", "composite", "save", "load"})
        for key in ("seed", "steps", "denoise", "model"):
            self.assertEqual(phase["sampler"]["inputs"][key], original["sampler"]["inputs"][key])
        self.assertEqual(phase["composite"], original["composite"])

    def test_encoding_prunes_denoiser_and_unrelated_output(self):
        graph = {"text": {"class_type": "Encode", "inputs": {}},
                 "save": {"class_type": "SaveRepairConditioning", "inputs": {"positive": ["text", 0]}},
                 "unet": {"class_type": "UNETLoader", "inputs": {}},
                 "unrelated": {"class_type": "SaveImage", "inputs": {"image": ["unet", 0]}}}
        self.assertEqual(set(prune(graph, ["save"])), {"text", "save"})


if __name__ == "__main__":
    unittest.main()
