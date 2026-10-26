"""Build a separate Linux runtime from the recorded source revisions and local models."""
import argparse
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import venv

ROOT = Path(__file__).resolve().parents[1]
CONSTRAINTS = ROOT / 'environment/ubuntu-2026-10-23/amd-constraints.txt'


def local_model_paths(models):
    return {'existing_local_models': {'base_path': str(models), **{name: name for name in (
        'diffusion_models', 'text_encoders', 'vae', 'checkpoints', 'loras',
        'embeddings', 'controlnet', 'clip_vision', 'upscale_models')}}}


def export_source(source, destination, revision):
    if destination.exists():
        raise FileExistsError(f'Refusing to overwrite source: {destination}')
    archive = subprocess.check_output(['git', '-C', str(source), 'archive', revision])
    destination.mkdir(parents=True)
    with tarfile.open(fileobj=io.BytesIO(archive)) as stream:
        stream.extractall(destination, filter='data')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime', type=Path, default=ROOT / 'runtime/ubuntu')
    parser.add_argument('--source', type=Path, default=ROOT.parent / 'amd_comfy/ComfyUI')
    parser.add_argument('--models', type=Path, default=ROOT.parent / 'amd_comfy/ComfyUI/models')
    parser.add_argument('--venv', type=Path, help='Optional SSD location; runtime/.venv links to it')
    parser.add_argument('--gguf-cpu-detach', action='store_true',
                        help='Apply the recorded CUDA-to-CPU mmap detach patch to this Linux copy')
    parser.add_argument('--gguf-clip-cpu-backing', action='store_true',
                        help='Install the experimental CLIP storage-reuse node; workflows must opt in')
    parser.add_argument('--deferred-vae', action='store_true',
                        help='Install the opt-in VAE loading dependency for text-only Qwen graphs')
    parser.add_argument('--checkpoint-components', action='store_true',
                        help='Install stock component-only checkpoint loaders for isolated AIO phases')
    parser.add_argument('--skip-install', action='store_true')
    args = parser.parse_args()
    if sys.platform != 'linux' or sys.version_info[:2] != (3, 12):
        parser.error('Run with Linux Python 3.12; the AMD wheel pins target CPython 3.12.')
    runtime, source, models = args.runtime.resolve(), args.source.resolve(), args.models.resolve()
    if not (models / 'diffusion_models').is_dir():
        parser.error(f'Existing model directory not found: {models}')
    revisions = json.loads((ROOT / 'environment/source-revisions.json').read_text())
    marker = runtime / 'source-revisions.json'
    if marker.exists():
        if json.loads(marker.read_text()) != revisions:
            raise ValueError('Existing runtime revisions differ; select a new runtime directory')
    else:
        export_source(source, runtime / 'ComfyUI', revisions['ComfyUI']['commit'])
        export_source(source / 'custom_nodes/ComfyUI-GGUF',
                      runtime / 'ComfyUI/custom_nodes/ComfyUI-GGUF', revisions['ComfyUI-GGUF']['commit'])
        marker.write_text(json.dumps(revisions, indent=2) + '\n')
    environment = args.venv.resolve() if args.venv else runtime / '.venv'
    link = runtime / '.venv'
    if args.venv and (link.exists() or link.is_symlink()) and link.resolve() != environment:
        raise FileExistsError('Existing runtime environment differs; preserve it and select a new runtime')
    python = environment / 'bin/python'
    if not python.exists():
        venv.EnvBuilder(with_pip=True, symlinks=False).create(environment)
    if args.venv and not link.exists() and not link.is_symlink():
        link.symlink_to(environment, target_is_directory=True)
    if not args.skip_install:
        lock = CONSTRAINTS.with_name('requirements-lock.txt')
        constraints = ['-c', str(CONSTRAINTS)]
        if lock.exists():
            constraints += ['-c', str(lock)]
        subprocess.run([str(python), '-m', 'pip', 'install', '--no-cache-dir', '--index-url',
            'https://repo.amd.com/rocm/whl-multi-arch/', '--extra-index-url',
            'https://pypi.org/simple', *constraints,
            'torch[device-gfx1032]==2.12.0+rocm7.14.0',
            'torchvision[device-gfx1032]==0.27.0+rocm7.14.0',
            'rocm[libraries,device-gfx1032]==7.14.0'], check=True)
        subprocess.run([str(python), '-m', 'pip', 'install', '--no-cache-dir',
            '--index-url', 'https://pypi.org/simple', *constraints,
            '-r', str(runtime / 'ComfyUI/requirements.txt'),
            '-r', str(runtime / 'ComfyUI/custom_nodes/ComfyUI-GGUF/requirements.txt')], check=True)
        subprocess.run([str(python), '-m', 'pip', 'check'], check=True)
    helper_nodes = ('repair_conditioning', 'feature_bench_ordering', 'gfx1032_quant_fallback',
                    'cpu_chunked_logits', 'gguf_mmap_offload', 'gguf_unload_trace')
    if args.gguf_clip_cpu_backing:
        helper_nodes += ('gguf_clip_cpu_backing',)
    if args.deferred_vae:
        helper_nodes += ('deferred_vae',)
    if args.checkpoint_components:
        helper_nodes += ('checkpoint_components',)
    for name in helper_nodes:
        target = runtime / 'ComfyUI/custom_nodes' / name
        if not target.exists():
            shutil.copytree(ROOT / 'code_source' / name, target, ignore=shutil.ignore_patterns('__pycache__'))
    paths = local_model_paths(models)
    # JSON is valid YAML and safely quotes paths containing spaces or non-ASCII characters.
    model_config = runtime / 'model-paths.yaml'
    if not model_config.exists():
        model_config.write_text(json.dumps(paths, ensure_ascii=False, indent=2) + '\n')
    input_source = ROOT / 'ComfyUI/input'
    if input_source.is_dir():
        for asset in input_source.rglob('*'):
            target = runtime / 'ComfyUI/input' / asset.relative_to(input_source)
            if asset.is_file() and not target.exists():
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(asset, target)
    subprocess.run([str(python), str(ROOT / 'scripts/apply_split_attention_patch.py'),
        '--runtime', str(runtime), '--record', str(runtime / 'split-attention-patch.json')], check=True)
    if args.gguf_cpu_detach:
        subprocess.run([str(python), str(ROOT / 'scripts/apply_gguf_cpu_detach_patch.py'),
            '--plugin', str(runtime / 'ComfyUI/custom_nodes/ComfyUI-GGUF'),
            '--record', str(runtime / 'gguf-cpu-detach-patch.json')], check=True)
    print(f'Ready for GPU checks: {python} {ROOT / "scripts/check_gpu.py"}')


if __name__ == '__main__':
    main()
