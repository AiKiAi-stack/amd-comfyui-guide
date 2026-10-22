"""Round-trip real tensors, shared storage, metadata and archive integrity."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest

import torch

ROOT = Path(__file__).resolve().parents[1]
(ROOT / "runs").mkdir(exist_ok=True)
folder_paths = types.ModuleType("folder_paths")
sys.modules["folder_paths"] = folder_paths
spec = importlib.util.spec_from_file_location("repair_conditioning", ROOT / "code_source/repair_conditioning/__init__.py")
archive = importlib.util.module_from_spec(spec)
spec.loader.exec_module(archive)


class ArchiveTests(unittest.TestCase):
    def test_nonfinite_latent_fails_before_writing_black_image_source(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "runs") as directory:
            folder_paths.get_input_directory = lambda: directory
            for invalid in (float("nan"), float("inf")):
                with self.assertRaisesRegex(ValueError, "Non-finite"):
                    archive.SaveRepairLatent().save({"samples": torch.tensor([invalid])}, "bad", "workflow")
            self.assertEqual(list(Path(directory).rglob("*.safetensors")), [])

    def test_old_nonfinite_archive_is_rejected_on_read(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "runs") as directory:
            path = Path(directory) / "invalid.safetensors"
            archive.save_file({"sample": torch.tensor([float("nan")])}, str(path), metadata={
                "repair_conditioning_version": "1", "tree": json.dumps(["tensor", "sample"])})
            with self.assertRaisesRegex(ValueError, "Non-finite"):
                archive.read_archive(path)

    def test_sampled_latent_nodes_preserve_dtype_and_mask(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "runs") as directory:
            folder_paths.get_input_directory = lambda: directory
            latent = {"samples": torch.randn(1, 16, 8, 8, dtype=torch.float16),
                      "noise_mask": torch.rand(8, 8)}
            saved = archive.SaveRepairLatent().save(latent, "sampled", "workflow")
            actual, = archive.LoadRepairLatent().load(saved["result"][0], saved["ui"]["archive_sha256"][0])
            for key in latent:
                self.assertEqual(actual[key].dtype, latent[key].dtype)
                self.assertTrue(torch.equal(actual[key], latent[key]))

    def test_exact_round_trip_and_shared_storage(self):
        shared = torch.arange(24, dtype=torch.float16).reshape(2, 3, 4)
        value = {"positive": [[shared, {"reference_latents": [shared], "strength": 1.0}]],
                 "negative": [[shared[:, :, ::2], {"flag": True, "none": None}]],
                 "latent": {"samples": torch.zeros(1, 4, 8, 8),
                            "noise_mask": torch.ones(8, 8, dtype=torch.bool),
                            "batch_index": (0, 1), "name": "test"}}
        with tempfile.TemporaryDirectory(dir=ROOT / "runs") as directory:
            path = Path(directory) / "conditions.safetensors"
            archive.write_archive(path, value, "source-graph-digest")
            restored = archive.read_archive(path)

        def equal(before, after):
            self.assertIs(type(before), type(after))
            if isinstance(before, torch.Tensor):
                self.assertEqual(before.dtype, after.dtype)
                self.assertTrue(torch.equal(before, after))
            elif isinstance(before, dict):
                self.assertEqual(before.keys(), after.keys())
                for key in before:
                    equal(before[key], after[key])
            elif isinstance(before, (list, tuple)):
                self.assertEqual(len(before), len(after))
                for left, right in zip(before, after):
                    equal(left, right)
            else:
                self.assertEqual(before, after)
        equal(value, restored)

    def test_unknown_metadata_is_rejected(self):
        with self.assertRaisesRegex(TypeError, "Unsupported conditioning"):
            archive.pack(object(), {})

    def test_loader_checks_hash_and_directory(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "runs") as directory:
            folder_paths.get_input_directory = lambda: directory
            result = archive.SaveRepairConditioning().save([], [], {"samples": torch.zeros(1)}, "case", "digest")
            relative = result["result"][0]
            digest = result["ui"]["archive_sha256"][0]
            self.assertEqual(archive.LoadRepairConditioning().load(relative, digest)[:2], ([], []))
            with self.assertRaisesRegex(ValueError, "checksum"):
                archive.LoadRepairConditioning().load(relative, "changed")
            with self.assertRaisesRegex(ValueError, "inside"):
                archive.LoadRepairConditioning().load("../outside.safetensors")


if __name__ == "__main__":
    unittest.main()
