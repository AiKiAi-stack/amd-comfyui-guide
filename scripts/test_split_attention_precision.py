"""Exercise ComfyUI split attention's FP16 score overflow and opt-in upcasting."""
import argparse
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--runtime", type=Path, required=True)
parser.add_argument("--baseline", action="store_true")
args = parser.parse_args()
sys.path.insert(0, str(args.runtime / "ComfyUI"))
sys.argv = [sys.argv[0], "--cpu", "--use-split-cross-attention"]
if not args.baseline:
    sys.argv.append("--force-upcast-attention")

import comfy.options
comfy.options.enable_args_parsing()
import torch
from comfy.ldm.modules import attention


class SplitAttentionTests(unittest.TestCase):
    def test_odd_query_length_retries_with_smaller_chunks(self):
        torch.manual_seed(7)
        q, k, v = (torch.randn(1, 5, 64) for _ in range(3))
        original_einsum = attention.einsum
        slices = []

        def budgeted_einsum(equation, left, right):
            if equation == "b i d, b j d -> b i j":
                slices.append(left.shape[1])
                if left.shape[1] > 2:
                    raise torch.OutOfMemoryError("Test score workspace allows two queries")
            return original_einsum(equation, left, right)

        with torch.inference_mode(), patch.object(attention.model_management, "get_free_memory", return_value=10000), \
                patch.object(attention, "einsum", side_effect=budgeted_einsum):
            actual = attention.attention_split(q, k, v, heads=1)
        expected = torch.softmax(q @ k.transpose(-1, -2) / 8, dim=-1) @ v
        self.assertIn(1, slices, "The final non-divisible query must be processed")
        torch.testing.assert_close(actual, expected, rtol=1e-5, atol=1e-5)

    def test_large_finite_qk_produces_finite_reference_attention(self):
        # q @ k overflows FP16 before the later scale multiplication. All
        # scores are equal, so the correct softmax is an exact uniform mean.
        q = torch.full((1, 4, 64), 128.0, dtype=torch.float16)
        k = q.clone()
        v = torch.arange(256, dtype=torch.float16).reshape(1, 4, 64) / 256
        with torch.inference_mode():
            actual = attention.attention_split(q, k, v, heads=1)
        self.assertTrue(torch.isfinite(actual).all().item(), "FP16 attention scores overflowed")
        expected = v.float().mean(dim=1, keepdim=True).expand_as(actual).half()
        torch.testing.assert_close(actual, expected, rtol=1e-3, atol=1e-3)


unittest.main(argv=["test_split_attention_precision"])
