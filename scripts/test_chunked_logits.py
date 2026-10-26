"""Exercise the real Qwen logits call site with a bounded workspace contract."""
import argparse
import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--runtime", type=Path, required=True)
parser.add_argument("--baseline", action="store_true")
args = parser.parse_args()
sys.argv = [sys.argv[0], "--cpu"]
sys.path.insert(0, str(args.runtime / "ComfyUI"))

import comfy.options
comfy.options.enable_args_parsing()
import torch
import comfy.ops
from comfy.text_encoders.llama import BaseQwen3
from comfy_kitchen.tensor import QuantizedTensor, TensorWiseINT8Layout

if not args.baseline:
    path = Path(__file__).resolve().parents[1] / "code_source/cpu_chunked_logits/bounded.py"
    spec = importlib.util.spec_from_file_location("bounded_logits", path)
    bounded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bounded)
    bounded.install()


class ChunkedLogitsTests(unittest.TestCase):
    def test_real_qwen_head_preserves_logits_without_full_vocab_dequant(self):
        torch.manual_seed(12)
        qdata = torch.randint(-100, 100, (4099, 32), dtype=torch.int8)
        params = TensorWiseINT8Layout.Params(scale=torch.rand(4099, 1) * 0.02,
            orig_dtype=torch.float16, orig_shape=(4099, 32), convrot=True, convrot_groupsize=16)
        weight = QuantizedTensor(qdata, "TensorWiseINT8Layout", params)
        ops = comfy.ops.mixed_precision_ops(compute_dtype=torch.float16, full_precision_mm=True)
        head = ops.Linear(32, 4099, bias=False, device="cpu")
        head.weight = torch.nn.Parameter(weight, requires_grad=False)
        model = SimpleNamespace(config=SimpleNamespace(lm_head=True), lm_head=head)
        instance = SimpleNamespace(model=model)
        x = torch.randn(2, 3, 32)
        with torch.inference_mode():
            # Direct unmodified head forward is the reference, even after installing the override.
            expected = head(x[:, -1:])
            original = TensorWiseINT8Layout.dequantize
            rows = []

            def budgeted(qdata, params):
                rows.append(qdata.shape[0])
                if qdata.shape[0] > 2048:
                    raise MemoryError(f"Full-vocabulary dequantization: {qdata.shape[0]} rows exceeds 2048-row workspace")
                return original(qdata, params)

            with patch.object(TensorWiseINT8Layout, "dequantize", side_effect=budgeted):
                actual = BaseQwen3.logits(instance, x)
        self.assertTrue(rows)
        self.assertLessEqual(max(rows), 2048)
        torch.testing.assert_close(actual, expected, rtol=1e-5, atol=1e-5)


unittest.main(argv=["test_chunked_logits"])
