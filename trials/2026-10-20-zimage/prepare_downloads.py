"""Pin the article's versions and obtain SHA-256 metadata before downloads."""
import importlib.util
import json
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
session = requests.Session()
session.mount('https://', HTTPAdapter(max_retries=Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])))

def metadata(repo, revision='main'):
    response = session.get(f'https://huggingface.co/api/models/{repo}/revision/{revision}', params={'blobs':'true'}, timeout=45)
    response.raise_for_status()
    data = response.json()
    name = repo.replace('/', '--') + '--' + data['sha'] + '.metadata.json'
    (HERE/name).write_text(json.dumps(data, indent=2), encoding='utf-8')
    return data

def prepare():
    specifications = [
        ('SeeSee21/Z-Image-Turbo-AIO', '3614ae1a6ceec70d8b1b02f41df3af72ac756241', 'z-image-turbo-fp8-aio.safetensors', 'checkpoints'),
        ('jayn7/Z-Image-Turbo-GGUF', 'main', 'z_image_turbo-Q4_K_M.gguf', 'diffusion_models'),
        ('unsloth/Qwen3-4B-GGUF', 'main', 'Qwen3-4B-Q4_K_M.gguf', 'text_encoders'),
        ('Comfy-Org/z_image_turbo', 'main', 'split_files/vae/ae.safetensors', 'vae'),
    ]
    manifest = []
    for repo, rev, filename, directory in specifications:
        data = metadata(repo, rev)
        record = next(f for f in data['siblings'] if f['rfilename'] == filename)
        manifest.append(dict(repo=repo, revision=data['sha'], file=filename, bytes=record['lfs']['size'],
                             sha256=record['lfs']['sha256'], target=str(ROOT/'ComfyUI/models'/directory/Path(filename).name)))
    (HERE/'download-manifest.json').write_text(json.dumps(manifest, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(manifest, indent=2), flush=True)
    return manifest

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--download', action='store_true')
    args = parser.parse_args()
    path = HERE/'download-manifest.json'
    manifest = json.loads(path.read_text(encoding='utf-8')) if path.exists() else prepare()
    if args.download:
        spec = importlib.util.spec_from_file_location('existing_downloader', ROOT/'trials/2026-10-18/download_weights.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.ROOT = HERE
        for item in sorted(manifest, key=lambda x:x['bytes']):
            module.download(item)
