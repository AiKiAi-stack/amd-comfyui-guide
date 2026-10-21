"""Regression at the real replay entry point using historical failure fixtures."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
WRONG = ROOT / "trials/2026-10-18/moss-wrong-timestep-api.json"


class ReplayPreflightTests(unittest.TestCase):
    def test_actual_noise_workflow_is_rejected_before_network(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            result = subprocess.run(
                [sys.executable, str(ROOT / "scripts/replay_workflow.py"), str(WRONG),
                 "--url", "http://127.0.0.1:1", "--out", str(Path(directory) / "result")],
                capture_output=True, text=True, timeout=20)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("MOSS timestep mismatch", result.stderr)
            self.assertNotIn("urlopen error", result.stderr)
            self.assertFalse((Path(directory) / "result").exists())

    def test_historical_corrected_workflows_pass(self):
        from workflow_checks import known_workflow_errors
        for name in ("moss-api.json", "moss8-api.json"):
            graph = json.loads((WRONG.parent / name).read_text(encoding="utf-8"))
            with self.subTest(name=name):
                self.assertEqual(known_workflow_errors(graph), [])

    def test_does_not_reject_sd3_on_unrelated_model(self):
        from workflow_checks import known_workflow_errors
        graph = json.loads(WRONG.read_text(encoding="utf-8"))
        graph["1"]["inputs"]["unet_name"] = "sd3.safetensors"
        self.assertEqual(known_workflow_errors(graph), [])

    def test_disconnected_bad_branch_does_not_block_valid_sampler(self):
        from workflow_checks import known_workflow_errors
        graph = json.loads(WRONG.read_text(encoding="utf-8"))
        graph["correct"] = {"class_type": "ModelSamplingAuraFlow", "inputs": {"model": ["1", 0], "shift": 5}}
        graph["8"]["inputs"]["model"] = ["correct", 0]
        self.assertEqual(known_workflow_errors(graph), [])

    def test_model_chain_cycle_terminates(self):
        from workflow_checks import known_workflow_errors
        graph = json.loads(WRONG.read_text(encoding="utf-8"))
        graph["7"]["inputs"]["model"] = ["11", 0]
        self.assertEqual(known_workflow_errors(graph), [])


if __name__ == "__main__":
    unittest.main()
