"""Exercise the installed GGUF pin callback with real mapped quantized bytes."""
import argparse
import hashlib
import importlib
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--runtime', type=Path, required=True)
parser.add_argument('--gguf', type=Path, required=True)
parser.add_argument('--gguf-node-dir', type=Path)
args = parser.parse_args()
sys.path.insert(0, str(args.runtime / 'ComfyUI'))
sys.argv = [sys.argv[0], '--cpu', '--disable-dynamic-vram']
import comfy.options
comfy.options.enable_args_parsing()
import torch
import gguf

package = types.ModuleType('cpu_detach_fixture')
package.__path__ = [str(args.gguf_node_dir or args.runtime / 'ComfyUI/custom_nodes/ComfyUI-GGUF')]
sys.modules[package.__name__] = package
ops = importlib.import_module(package.__name__ + '.ops')
nodes = importlib.import_module(package.__name__ + '.nodes')


class CpuDetachTests(unittest.TestCase):
    def test_cpu_only_pin_keeps_existing_storage(self):
        model = torch.nn.Module()
        model.layer = torch.nn.Linear(4, 2, bias=True)
        original = model.layer.weight.data_ptr()
        expected = model.layer.weight.detach().clone()
        patcher = nodes.GGUFModelPatcher(model, torch.device('cpu'), torch.device('cpu'))
        patcher.named_modules_to_munmap = {'layer': model.layer}
        try:
            patcher.pin_weight_to_device('layer.weight')
            self.assertEqual(model.layer.weight.data_ptr(), original)
            self.assertTrue(torch.equal(model.layer.weight, expected))
            self.assertNotIn('layer', patcher.named_modules_to_munmap)
        finally:
            patcher.cleanup()

    def test_real_pin_callback_detaches_mmap_without_gpu_workspace(self):
        reader = gguf.GGUFReader(str(args.gguf))
        candidates = [t for t in reader.tensors if t.tensor_type == gguf.GGMLQuantizationType.Q4_K
                      and t.data.nbytes <= 16 * 1024**2]
        self.assertTrue(candidates, 'Fixture needs a real Q4_K tensor within the 16MiB budget')
        source = min(candidates, key=lambda t: t.data.nbytes)
        raw = torch.from_numpy(source.data)
        original = ops.GGMLTensor(raw, tensor_type=source.tensor_type,
                                 tensor_shape=torch.Size(reversed(source.shape.tolist())),
                                 patches=[('preserve-metadata', 'layer.weight')])
        expected = hashlib.sha256(raw.numpy().tobytes()).hexdigest()
        model = torch.nn.Module()
        model.layer = torch.nn.Module()
        model.layer.register_parameter('weight', torch.nn.Parameter(original, requires_grad=False))
        model.layer.register_parameter('bias', torch.nn.Parameter(torch.tensor([2.5]), requires_grad=False))
        model.layer.register_buffer('offset', torch.tensor([3.5]))
        patcher = nodes.GGUFModelPatcher(model, torch.device('cuda'), torch.device('cpu'))
        patcher.named_modules_to_munmap = {'layer': model.layer}
        old_to = model.layer.to

        def bounded_to(device, *positional, **keywords):
            if torch.device(device).type != 'cpu':
                raise AssertionError('CPU mmap detachment requested GPU staging workspace')
            return old_to(device, *positional, **keywords)

        try:
            with patch.object(model.layer, 'to', side_effect=bounded_to):
                patcher.pin_weight_to_device('layer.weight')
            actual = model.layer.weight
            self.assertIsInstance(actual, ops.GGMLTensor)
            self.assertNotEqual(actual.data_ptr(), raw.data_ptr())
            self.assertEqual(actual.device.type, 'cpu')
            self.assertEqual(actual.tensor_type, original.tensor_type)
            self.assertEqual(actual.tensor_shape, original.tensor_shape)
            self.assertEqual(actual.patches, original.patches)
            self.assertFalse(actual.requires_grad)
            self.assertEqual(hashlib.sha256(actual.as_subclass(torch.Tensor).numpy().tobytes()).hexdigest(), expected)
            self.assertEqual(hashlib.sha256(raw.numpy().tobytes()).hexdigest(), expected)
            self.assertEqual(model.layer.bias.item(), 2.5)
            self.assertEqual(model.layer.offset.item(), 3.5)
            self.assertNotIn('layer', patcher.named_modules_to_munmap)
            patcher.pin_weight_to_device('layer.weight')
            self.assertEqual(hashlib.sha256(actual.as_subclass(torch.Tensor).numpy().tobytes()).hexdigest(), expected)
        finally:
            patcher.cleanup()


if __name__ == '__main__':
    unittest.main(argv=[sys.argv[0]])
