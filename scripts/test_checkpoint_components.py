"""Ensure component-only nodes delegate exact stock flags and output slots."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import Mock, patch

path = Path(__file__).resolve().parents[1] / 'code_source/checkpoint_components/__init__.py'
spec = importlib.util.spec_from_file_location('checkpoint_components', path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ComponentTests(unittest.TestCase):
    def setUp(self):
        self.objects = tuple(object() for _ in range(4))
        self.loader = Mock(return_value=self.objects)
        sd = types.ModuleType('comfy.sd');sd.load_checkpoint_guess_config = self.loader
        comfy = types.ModuleType('comfy');comfy.sd = sd
        folders = types.ModuleType('folder_paths')
        folders.get_full_path_or_raise = lambda kind, name: '/models/' + name
        folders.get_folder_paths = lambda kind: ['/embeddings']
        self.scope = patch.dict(sys.modules, {'comfy': comfy, 'comfy.sd': sd, 'folder_paths': folders})
        self.scope.start();self.addCleanup(self.scope.stop)

    def test_clip_only_never_instantiates_diffusion_or_vae(self):
        self.assertEqual(module.LoadCheckpointClipOnly().load('aio.safetensors'), (self.objects[1],))
        self.loader.assert_called_once_with('/models/aio.safetensors', output_model=False, output_clip=True,
            output_vae=False, output_clipvision=False, embedding_directory=['/embeddings'])

    def test_sampling_components_do_not_instantiate_text_encoder(self):
        self.assertEqual(module.LoadCheckpointModelVaeOnly().load('aio.safetensors'), (self.objects[0], self.objects[2]))
        self.loader.assert_called_once_with('/models/aio.safetensors', output_model=True, output_clip=False,
            output_vae=True, output_clipvision=False, embedding_directory=['/embeddings'])


if __name__ == '__main__': unittest.main()
