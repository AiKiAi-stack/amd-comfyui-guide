"""Round-trip real tensors, shared storage, metadata and archive integrity."""
import importlib.util
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
