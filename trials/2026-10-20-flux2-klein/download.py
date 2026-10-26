"""Pin and download the three components named by ComfyUI's Klein 4B template."""
import importlib.util
import json
from pathlib import Path

import requests

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def prepare():
    specifications = [
        ('black-forest-labs/FLUX.2-klein-4b-fp8', 'flux-2-klein-4b-fp8.safetensors', 'diffusion_models'),
        ('Comfy-Org/flux2-klein-4B', 'split_files/text_encoders/qwen_3_4b.safetensors', 'text_encoders'),
        ('Comfy-Org/flux2-klein-4B', 'split_files/vae/flux2-vae.safetensors', 'vae'),
    ]
    sources = {}
    manifest = []
    for repo, filename, directory in specifications:
        if repo not in sources:
            cached = HERE / ('fp8-source-metadata.json' if repo.startswith('black-forest-labs/') else 'comfy-source-metadata.json')
            if cached.exists():
                metadata = json.loads(cached.read_text(encoding='utf-8'))
            else:
                response = requests.get('https://huggingface.co/api/models/' + repo, params={'blobs': 'true'}, timeout=30)
                response.raise_for_status()
                metadata = response.json()
                cached.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding='utf-8')
            sources[repo] = metadata
        metadata = sources[repo]
        file = next(item for item in metadata['siblings'] if item['rfilename'] == filename)
        manifest.append({'repo': repo, 'revision': metadata['sha'], 'file': filename,
                         'bytes': file['lfs']['size'], 'sha256': file['lfs']['sha256'],
                         'target': str(ROOT / 'ComfyUI/models' / directory / Path(filename).name)})
    (HERE / 'download-manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    return manifest


if __name__ == '__main__':
    manifest = prepare()
    spec = importlib.util.spec_from_file_location('existing_downloader', ROOT / 'trials/2026-10-18/download_weights.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.ROOT = HERE
    for item in sorted(manifest, key=lambda item: item['bytes']):
        module.download(item)
