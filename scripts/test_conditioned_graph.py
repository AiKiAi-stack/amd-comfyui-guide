"""Check that phase splitting preserves actual sampling and output dependencies."""
import copy
from pathlib import Path
import unittest

from run_conditioned_repair import conditioning_node, conditioning_signature, latent_decode_graph, latent_sampling_graph, prune, reuse_text_graph, sampling_signature
from run_qwen_reference_repair import cached_reference_graph, reference_phase_graph


class GraphTests(unittest.TestCase):
    def test_actual_turbo_reference_and_text_phases_do_not_share_models(self):
        import json
        path = Path(__file__).resolve().parents[1] / 'trials/2026-10-21-repairs/workflows/turbo-fox-profile-natural.api.json'
        graph = json.loads(path.read_text(encoding='utf-8'))
        references = reference_phase_graph(graph, '4', '64', 'probe', 'source-sha')
        self.assertIn('3', references)  # VAE
        self.assertNotIn('2', references)  # text model
        self.assertNotIn('1', references)  # diffusion model
        self.assertNotIn('4', references)
        self.assertEqual(references['repair_save_references']['inputs']['initial_latent'], ['55', 0])
        cached = cached_reference_graph(graph, '4', '64', 'repair_conditioning/cache.safetensors', 'sha')
        cached['save'] = {'class_type': 'SaveRepairConditioning', 'inputs': {
            'positive': ['4', 0], 'negative': ['4', 1], 'latent': ['4', 2]}}
        encoding = prune(cached, ['save'])
        self.assertIn('2', encoding)
        self.assertNotIn('3', encoding)
        self.assertEqual(encoding['4']['inputs']['expected_sha256'], 'sha')

    def test_reference_isolation_handles_core_empty_latent_and_rejects_text_dependency(self):
        graph = {'clip': {'class_type': 'CLIPLoader', 'inputs': {}},
                 'image': {'class_type': 'LoadImage', 'inputs': {}},
                 'vae': {'class_type': 'VAELoader', 'inputs': {}},
                 'text': {'class_type': 'TextEncodeQwenImage21', 'inputs': {
                     'clip': ['clip', 0], 'vae': ['vae', 0], 'images.image_1': ['image', 0]}},
                 'sampler': {'class_type': 'KSampler', 'inputs': {'latent_image': ['text', 2]}}}
        refs = reference_phase_graph(graph, 'text', 'sampler', 'case', 'sha')
        self.assertNotIn('initial_latent', refs['repair_save_references']['inputs'])
        graph['mask'] = {'class_type': 'SetLatentNoiseMask', 'inputs': {'samples': ['text', 2]}}
        graph['sampler']['inputs']['latent_image'] = ['mask', 0]
        with self.assertRaises(ValueError):
            reference_phase_graph(graph, 'text', 'sampler', 'case', 'sha')

    def test_reuse_text_keeps_new_initial_latent_and_prunes_encoder(self):
        graph = {'clip': {'class_type': 'CLIPLoader', 'inputs': {'clip_name': 'original'}},
                 'text': {'class_type': 'Encode', 'inputs': {'clip': ['clip', 0], 'prompt': 'fox'}},
                 'image': {'class_type': 'LoadImage', 'inputs': {'image': 'old.png'}},
                 'latent': {'class_type': 'VAEEncode', 'inputs': {'pixels': ['image', 0]}},
                 'repair_save_conditions': {'class_type': 'SaveRepairConditioning', 'inputs': {
                     'positive': ['text', 0], 'negative': ['text', 1], 'latent': ['latent', 0]}}}
        changed = copy.deepcopy(graph)
        changed['image']['inputs']['image'] = 'cat-removed.png'
        result = reuse_text_graph(changed, graph, 'repair_conditioning/exact.safetensors', 'sha')
        self.assertNotIn('clip', result)
        self.assertNotIn('text', result)
        self.assertEqual(result['image'], changed['image'])
        self.assertEqual(result['repair_save_conditions']['inputs']['latent'], ['latent', 0])
        self.assertEqual(result['repair_reuse_text']['inputs']['expected_sha256'], 'sha')
        for key, value in [('prompt', 'cat'), ('clip', ['different', 0])]:
            invalid = copy.deepcopy(changed)
            invalid['text']['inputs'][key] = value
            if key == 'clip':
                invalid['different'] = copy.deepcopy(invalid['clip'])
            with self.assertRaises(ValueError):
                reuse_text_graph(invalid, graph, 'repair_conditioning/exact.safetensors', 'sha')

    def test_reuse_text_rejects_reference_or_output_slot_change(self):
        graph = {'reference': {'class_type': 'LoadImage', 'inputs': {'image': 'identity-a.png'}},
                 'text': {'class_type': 'Encode', 'inputs': {'image': ['reference', 0]}},
                 'repair_save_conditions': {'class_type': 'SaveRepairConditioning', 'inputs': {
                     'positive': ['text', 0], 'negative': ['text', 1], 'latent': ['text', 2]}}}
        for change in ('reference', 'slot'):
            invalid = copy.deepcopy(graph)
            if change == 'reference':
                invalid['reference']['inputs']['image'] = 'identity-b.png'
            else:
                invalid['repair_save_conditions']['inputs']['negative'] = ['text', 0]
            with self.assertRaises(ValueError):
                reuse_text_graph(invalid, graph, 'repair_conditioning/exact.safetensors', 'sha')

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
