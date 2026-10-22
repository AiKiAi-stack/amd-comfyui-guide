"""Check that phase splitting preserves actual sampling and output dependencies."""
import copy
from pathlib import Path
import unittest

from run_conditioned_repair import conditioning_node, conditioning_signature, latent_decode_graph, latent_sampling_graph, prune, sampling_signature


class GraphTests(unittest.TestCase):
    def test_sample_reuse_ignores_provenance_only_and_rejects_seed_change(self):
        graph = {"sampler": {"class_type": "KSampler", "inputs": {"seed": 1}},
                 "repair_save_latent": {"class_type": "SaveRepairLatent", "inputs": {
                     "latent": ["sampler", 0], "workflow_sha256": "old-attachment-graph"}}}
        same = copy.deepcopy(graph)
        same["repair_save_latent"]["inputs"]["workflow_sha256"] = "fixed-output-attachments"
        self.assertEqual(sampling_signature(graph), sampling_signature(same))
        same["sampler"]["inputs"]["seed"] = 2
        self.assertNotEqual(sampling_signature(graph), sampling_signature(same))

    def test_actual_turbo_custom_guider_encoding_excludes_denoiser(self):
        import json
        path = Path(__file__).resolve().parents[1] / "trials/2026-10-21-repairs/workflows/turbo-mask-fox-reference.api.json"
        graph = json.loads(path.read_text(encoding="utf-8"))
        sampler_id = next(k for k, n in graph.items() if n["class_type"] == "SamplerCustomAdvanced")
        guider_id = conditioning_node(graph, sampler_id)
        inputs = graph[guider_id]["inputs"]
        graph["save"] = {"class_type": "SaveRepairConditioning", "inputs": {
            "positive": inputs["positive"], "negative": inputs["negative"],
            "latent": graph[sampler_id]["inputs"]["latent_image"]}}
        encoding = prune(graph, ["save"])
        self.assertNotIn(sampler_id, encoding)
        self.assertNotIn(guider_id, encoding)
        self.assertFalse(any(n["class_type"] == "UnetLoaderGGUF" for n in encoding.values()))
        self.assertTrue(any(n["class_type"] == "TextEncodeQwenImage21" for n in encoding.values()))

    def test_decode_split_retains_composite_without_model(self):
        graph = {"model": {"class_type": "UNETLoader", "inputs": {}},
                 "sampler": {"class_type": "KSampler", "inputs": {"model": ["model", 0]}},
                 "vae": {"class_type": "VAELoader", "inputs": {}},
                 "decode": {"class_type": "VAEDecode", "inputs": {"vae": ["vae", 0], "samples": ["sampler", 0]}},
                 "input": {"class_type": "LoadImage", "inputs": {}},
                 "composite": {"class_type": "ImageCompositeMasked", "inputs": {"source": ["decode", 0], "destination": ["input", 0]}},
                 "save": {"class_type": "SaveImage", "inputs": {"images": ["composite", 0]}}}
        sample = latent_sampling_graph(graph, "sampler", "case", "source-sha")
        self.assertEqual(set(sample), {"model", "sampler", "repair_save_latent"})
        decode = latent_decode_graph(graph, "sampler", ["save"], "repair_conditioning/x.safetensors", "latent-sha")
        self.assertNotIn("model", decode)
        self.assertEqual(decode["composite"], graph["composite"])
        self.assertEqual(decode["sampler"]["inputs"]["expected_sha256"], "latent-sha")

    def test_archive_reuse_rejects_prompt_or_latent_changes(self):
        graph = {"text": {"class_type": "Encode", "inputs": {"prompt": "cat"}},
                 "repair_save_conditions": {"class_type": "SaveRepairConditioning", "inputs": {
                     "positive": ["text", 0], "workflow_sha256": "original"}}}
        same = copy.deepcopy(graph)
        same["repair_save_conditions"]["inputs"]["workflow_sha256"] = "model-cache-option-changed"
        self.assertEqual(conditioning_signature(graph), conditioning_signature(same))
        same["text"]["inputs"]["prompt"] = "fox"
        self.assertNotEqual(conditioning_signature(graph), conditioning_signature(same))

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
