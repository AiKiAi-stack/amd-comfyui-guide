"""Isolate Qwen 2.1 reference VAE, GPU text encoding, sampling and CPU decode."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys

from run_conditioned_repair import prune
from workflow_checks import known_workflow_errors


def reference_phase_graph(graph, text_id, sampler_id, label, digest):
    inputs = graph[text_id]['inputs']
    if 'vae' not in inputs or 'images.image_1' not in inputs:
        raise ValueError('Use TextEncodeQwenImage21 with a VAE and at least one image')
    if any(key.startswith('images.image_') and key not in {'images.image_1', 'images.image_2'} for key in inputs):
        raise ValueError('This bounded reference runner supports one or two images')
    reference = copy.deepcopy(graph)
    saved = {'vae': inputs['vae'], 'image1': inputs['images.image_1'],
             'resolution': inputs.get('resolution', 1024), 'prefix': label + '-refs', 'workflow_sha256': digest}
    if 'images.image_2' in inputs:
        saved['image2'] = inputs['images.image_2']
    initial = graph[sampler_id]['inputs']['latent_image']
    if initial != [text_id, 2]:
        if text_id in prune(graph, [initial[0]]):
            raise ValueError('Initial latent depends on the text encoder; cannot isolate reference VAE')
        saved['initial_latent'] = initial
    reference['repair_save_references'] = {'class_type': 'SaveRepairQwenReferences', 'inputs': saved}
    return prune(reference, ['repair_save_references'])


def cached_reference_graph(graph, text_id, sampler_id, relative, digest):
    result = copy.deepcopy(graph)
    old = graph[text_id]['inputs']
    result[text_id] = {'class_type': 'TextEncodeRepairQwenReferences', 'inputs': {
        'clip': old['clip'], 'prompt': old['prompt'], 'negative_prompt': old['negative_prompt'],
        'file': relative, 'expected_sha256': digest}}
    result[sampler_id]['inputs']['latent_image'] = [text_id, 2]
    return result


def prepare_workflow(path):
    graph = json.loads(path.read_text(encoding='utf-8'))
    errors = known_workflow_errors(graph)
    if errors:
        raise ValueError('; '.join(errors))
    texts = [key for key, node in graph.items() if node['class_type'] == 'TextEncodeQwenImage21']
    samplers = [key for key, node in graph.items() if node['class_type'] in {'KSampler', 'SamplerCustomAdvanced'}]
    if len(texts) != 1 or len(samplers) != 1:
        raise ValueError('Use one Qwen 2.1 encoder and one sampler per workflow')
    label = path.stem.removesuffix('.api')
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    reference = reference_phase_graph(graph, texts[0], samplers[0], label, digest)
    return {'graph': graph, 'text': texts[0], 'sampler': samplers[0],
            'label': label, 'digest': digest, 'reference': reference}


def prepare_workflows(paths):
    specs = [prepare_workflow(path) for path in paths]
    if len({spec['label'] for spec in specs}) != len(specs):
        raise ValueError('Workflow labels must be unique across the batch')
    return specs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime', type=Path, required=True)
    parser.add_argument('--workflow', type=Path, nargs='+', required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--model-paths', type=Path)
    parser.add_argument('--python-executable', type=Path)
    args = parser.parse_args()
    try:
        specs = prepare_workflows(args.workflow)
    except ValueError as error:
        parser.error(str(error))
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    ref_paths = []
    for spec in specs:
        ref_path = out / (spec['label'] + '-references.api.json')
        ref_path.write_text(json.dumps(spec['reference'], indent=2), encoding='utf-8')
        ref_paths.append(ref_path)
    common = ['--runtime', str(args.runtime.resolve())]
    if args.model_paths:
        common += ['--model-paths', str(args.model_paths.resolve())]
    if args.python_executable:
        common += ['--python-executable', str(args.python_executable.resolve())]
    scripts = Path(__file__).resolve().parent
    subprocess.run([sys.executable, str(scripts / 'run_repair_batch.py'), *common,
        '--workflow', *map(str, ref_paths), '--out', str(out / 'reference-precompute'), '--profile', 'cpu-only'], check=True)
    summary = json.loads((out / 'reference-precompute/summary.json').read_text(encoding='utf-8'))
    if not summary.get('server_stopped'):
        raise ValueError('Reference VAE process must exit before loading the text model')
    cached_dir = out / 'cached'
    cached_dir.mkdir()
    links = {}
    cached_paths = []
    for spec in specs:
        label = spec['label']
        ref_case = out / 'reference-precompute/cases' / (label + '-references')
        history = json.loads((ref_case / 'history.json').read_text(encoding='utf-8'))
        entry = next(iter(history.values()))
        if entry['status']['status_str'] != 'success':
            raise ValueError('Reference precompute did not succeed')
        saved = entry['outputs']['repair_save_references']
        relative, archive_sha = saved['text'][0], saved['archive_sha256'][0]
        archive_root = (args.runtime / 'ComfyUI/input/repair_conditioning').resolve()
        archive = (archive_root.parent / relative).resolve()
        if not archive.is_relative_to(archive_root) or hashlib.sha256(archive.read_bytes()).hexdigest() != archive_sha:
            raise ValueError('Reference archive path or checksum changed')
        cached = cached_reference_graph(spec['graph'], spec['text'], spec['sampler'], relative, archive_sha)
        cached_path = cached_dir / (label + '.api.json')
        cached_path.write_text(json.dumps(cached, indent=2), encoding='utf-8')
        cached_paths.append(cached_path)
        links[label] = {'original_workflow_sha256': spec['digest'],
            'cached_workflow_sha256': hashlib.sha256(cached_path.read_bytes()).hexdigest(),
            'archive_file': relative, 'archive_sha256': archive_sha,
            'reference_api_sha256': hashlib.sha256((ref_case / 'api.json').read_bytes()).hexdigest(),
            'reference_history_sha256': hashlib.sha256((ref_case / 'history.json').read_bytes()).hexdigest(),
            'reference_process_exited_before_text_encoding': True,
            'meaning': 'Installed core resize/alpha/VAE reference preparation; exact cached latents, no resident VAE during TE'}
    (out / 'reference-link.json').write_text(json.dumps(next(iter(links.values())) if len(links) == 1 else links, indent=2), encoding='utf-8')
    subprocess.run([sys.executable, str(scripts / 'run_conditioned_repair.py'), *common,
        '--workflow', *map(str, cached_paths), '--out', str(out / 'phases'),
        '--encoding-profile', 'gpu-text-dynamic', '--encode-extra-arg=--disable-pinned-memory',
        '--encode-extra-arg=--fp16-text-enc', '--encode-extra-arg=--force-upcast-attention',
        '--sampling-profile', 'gpu-text', '--sample-extra-arg=--fp16-unet',
        '--sample-extra-arg=--force-upcast-attention', '--isolate-sampling', '--isolate-decode'], check=True)
    for label, provenance in links.items():
        phase_file = out / 'phases/graphs' / label / 'phase-link.json'
        phase = json.loads(phase_file.read_text(encoding='utf-8'))
        phase['reference_precompute'] = provenance
        phase_file.write_text(json.dumps(phase, indent=2), encoding='utf-8')
    print('REFERENCE-ISOLATED EXECUTION COMPLETE; visual review required', flush=True)


if __name__ == '__main__':
    main()
