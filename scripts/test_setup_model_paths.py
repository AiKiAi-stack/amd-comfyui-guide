"""A migrated model directory need not be named 'models'."""
from pathlib import Path
import unittest
from setup_ubuntu import local_model_paths


class ModelPathTests(unittest.TestCase):
    def test_arbitrary_migrated_directory_resolves_under_that_directory(self):
        model_root = Path('/media/user/MODELS/AIModels/comfyui-models-20261024')
        entry = local_model_paths(model_root)['existing_local_models']
        self.assertEqual(Path(entry['base_path']) / entry['diffusion_models'], model_root / 'diffusion_models')
        self.assertEqual(Path(entry['base_path']) / entry['text_encoders'], model_root / 'text_encoders')

    def test_original_models_directory_keeps_same_effective_paths(self):
        model_root = Path('/original/ComfyUI/models')
        entry = local_model_paths(model_root)['existing_local_models']
        for key in ('diffusion_models', 'text_encoders', 'vae', 'loras'):
            self.assertEqual(Path(entry['base_path']) / entry[key], model_root / key)


if __name__ == '__main__': unittest.main()
