"""Exercise real GGUF unpatch with no workspace for another GPU-to-CPU weight copy."""
import argparse
import copy
import gc
import hashlib
import importlib
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--runtime', type=Path, required=True)
parser.add_argument('--gguf', type=Path, required=True)
parser.add_argument('--baseline', action='store_true')
args = parser.parse_args()
sys.path.insert(0, str(args.runtime / 'ComfyUI'))
sys.argv = [sys.argv[0], '--disable-dynamic-vram']
import comfy.options
comfy.options.enable_args_parsing()
import torch
import gguf

package = types.ModuleType('clip_backing_fixture')
package.__path__ = [str(args.runtime / 'ComfyUI/custom_nodes/ComfyUI-GGUF')]
sys.modules[package.__name__] = package
ops = importlib.import_module(package.__name__ + '.ops')
nodes = importlib.import_module(package.__name__ + '.nodes')


class Clip:
    def __init__(self, patcher):
        self.patcher = patcher

    def clone(self):
        result = copy.copy(self)
        result.patcher = self.patcher.clone()
        return result


class CpuBackingTests(unittest.TestCase):
    def fixture(self):
        self.reader = gguf.GGUFReader(str(args.gguf))
        tensor = min((t for t in self.reader.tensors if t.tensor_type == gguf.GGMLQuantizationType.Q4_K
                      and t.data.nbytes <= 16 * 1024**2), key=lambda t: t.data.nbytes)
        raw = torch.from_numpy(tensor.data)
        model = torch.nn.Module()
        model.layer = torch.nn.Module()
        weight = ops.GGMLTensor(raw, tensor_type=tensor.tensor_type,
            tensor_shape=torch.Size(reversed(tensor.shape.tolist())), patches=[])
        model.layer.register_parameter('weight', torch.nn.Parameter(weight, requires_grad=False))
        # Some floating CLIP norm/bias parameters retain PyTorch's default flag.
        model.layer.register_parameter('bias', torch.nn.Parameter(torch.tensor([2.5]), requires_grad=True))
        model.layer.register_buffer('offset', torch.tensor([3.5]))
        patcher = nodes.GGUFModelPatcher(model, torch.device('cuda'), torch.device('cpu'))
        # Actual core CLIP always installs this non-weight compute policy.
        patcher.set_model_compute_dtype(torch.float32)
        return model, patcher, raw

    def candidate(self):
        path = Path(__file__).resolve().parents[1] / 'code_source/gguf_clip_cpu_backing/__init__.py'
        spec = importlib.util.spec_from_file_location('clip_candidate', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_real_unpatch_reuses_original_cpu_storage(self):
        model, stock, raw = self.fixture()
        original_ptr = model.layer.weight.data_ptr()
        expected = hashlib.sha256(raw.numpy().tobytes()).hexdigest()
        original_method = nodes.GGUFModelPatcher.unpatch_model
        active = stock if args.baseline else self.candidate().RetainGgufClipCpuBacking().enable(Clip(stock))[0].patcher
        original_to = ops.GGMLTensor.to

        def no_copy(tensor, *positional, **keywords):
            device = keywords.get('device', positional[0] if positional else None)
            if device is not None and not isinstance(device, torch.dtype):
                if tensor.device.type == 'cuda' and torch.device(device).type == 'cpu':
                    raise AssertionError('Unpatch requested a fresh GPU-to-CPU weight copy')
            return original_to(tensor, *positional, **keywords)

        try:
            torch.cuda.synchronize()
            initial_allocated = torch.cuda.memory_allocated()
            for _ in range(3):
                model.to('cuda')
                with patch.object(ops.GGMLTensor, 'to', new=no_copy):
                    active.unpatch_model(device_to=torch.device('cpu'))
                actual = model.layer.weight
                self.assertEqual(actual.device.type, 'cpu')
                self.assertEqual(actual.data_ptr(), original_ptr)
                self.assertEqual(actual.tensor_type, gguf.GGMLQuantizationType.Q4_K)
                self.assertEqual(actual.patches, [])
                self.assertEqual(hashlib.sha256(actual.as_subclass(torch.Tensor).numpy().tobytes()).hexdigest(), expected)
                self.assertEqual(model.layer.bias.item(), 2.5)
                self.assertTrue(model.layer.bias.requires_grad)
                self.assertEqual(model.layer.offset.device.type, 'cpu')
                self.assertEqual(model.layer.offset.item(), 3.5)
                torch.cuda.synchronize()
                self.assertLessEqual(torch.cuda.memory_allocated() - initial_allocated, 2 * 1024**2,
                                     'Restoring CPU weights must release their GPU allocation')
            self.assertIs(nodes.GGUFModelPatcher.unpatch_model, original_method)
            if not args.baseline:
                self.assertIsNot(type(active), type(stock))
                self.assertIsNone(active.parent)
                clone = active.clone()
                self.assertIs(type(clone), type(active))
                self.assertIs(clone.parent, active)
                clone.cleanup()
                for base, _, _, _ in model._lab_clip_cpu_backing.values():
                    self.assertIsNone(base._base, 'Backing must not retain a moving GPU Parameter via view base')
        finally:
            model.to('cpu')
            active.cleanup()
            stock.cleanup()
            del active, stock, model
            gc.collect()
            torch.cuda.empty_cache()

    @unittest.skipIf(args.baseline, 'Candidate policy test')
    def test_partial_offload_uses_full_cpu_restore_without_copy(self):
        model, stock, raw = self.fixture()
        active = self.candidate().RetainGgufClipCpuBacking().enable(Clip(stock))[0].patcher
        original_to = ops.GGMLTensor.to
        original_ptr = model.layer.weight.data_ptr()
        loaded_bytes = raw.numel() * raw.element_size() + model.layer.bias.numel() * 4

        def no_copy(tensor, *positional, **keywords):
            device = keywords.get('device', positional[0] if positional else None)
            if device is not None and not isinstance(device, torch.dtype):
                if tensor.device.type == 'cuda' and torch.device(device).type == 'cpu':
                    raise AssertionError('Partial unload requested a fresh GPU-to-CPU weight copy')
            return original_to(tensor, *positional, **keywords)

        try:
            model.to('cuda')
            model.layer.comfy_patched_weights = True
            model.model_loaded_weight_memory = loaded_bytes
            with patch.object(ops.GGMLTensor, 'to', new=no_copy):
                freed = active.partially_unload(torch.device('cpu'), memory_to_free=1)
            self.assertEqual(freed, loaded_bytes)
            self.assertEqual(active.loaded_size(), 0)
            self.assertEqual(model.layer.weight.data_ptr(), original_ptr)
            self.assertEqual(model.layer.weight.device.type, 'cpu')
        finally:
            with torch.inference_mode():
                model.to('cpu')
            active.cleanup()
            stock.cleanup()

    @unittest.skipIf(args.baseline, 'Candidate policy test')
    def test_inference_storage_survives_free_outside_context(self):
        model, stock, _ = self.fixture()
        active = None
        try:
            with torch.inference_mode():
                model.layer.bias = torch.nn.Parameter(torch.tensor([2.5]), requires_grad=True)
                original_ptr = model.layer.bias.data_ptr()
                active = self.candidate().RetainGgufClipCpuBacking().enable(Clip(stock))[0].patcher
                model.to('cuda')
            self.assertFalse(torch.is_inference_mode_enabled())
            active.unpatch_model(device_to=torch.device('cpu'))
            self.assertEqual(model.layer.bias.data_ptr(), original_ptr)
            self.assertTrue(model.layer.bias.requires_grad)
            self.assertEqual(model.layer.bias.item(), 2.5)
            late_clone = active.clone()
            late_clone.patches = {'layer.weight': ['unsupported-late-LoRA']}
            with self.assertRaisesRegex(ValueError, 'LoRA'):
                late_clone.patch_model(device_to=torch.device('cuda'))
            late_clone.cleanup()
        finally:
            with torch.inference_mode():
                model.to('cpu')
            if active is not None:
                active.cleanup()
            stock.cleanup()

    @unittest.skipIf(args.baseline, 'Candidate policy test')
    def test_lora_and_non_cpu_initial_weights_are_refused(self):
        model, stock, _ = self.fixture()
        try:
            stock.patches = {'layer.weight': ['not-supported-in-this-experiment']}
            with self.assertRaisesRegex(ValueError, 'LoRA'):
                self.candidate().RetainGgufClipCpuBacking().enable(Clip(stock))
            stock.patches = {}
            stock.add_object_patch('unsupported', object())
            with self.assertRaisesRegex(ValueError, 'patches'):
                self.candidate().RetainGgufClipCpuBacking().enable(Clip(stock))
            stock.object_patches.pop('unsupported')
            model.to('cuda')
            with self.assertRaisesRegex(ValueError, 'before'):
                self.candidate().RetainGgufClipCpuBacking().enable(Clip(stock))
        finally:
            model.to('cpu')
            stock.cleanup()


if __name__ == '__main__':
    unittest.main(argv=[sys.argv[0]])
