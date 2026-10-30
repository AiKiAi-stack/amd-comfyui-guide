"""Keep one owned Linux service; archive and /free between Qwen's three phases."""
import argparse
import copy
import hashlib
import json
import os
import signal
from pathlib import Path
import subprocess
import sys
import time
from urllib.request import Request, urlopen

import psutil

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from run_conditioned_repair import prune, latent_sampling_graph, latent_decode_graph
from run_repair_batch import stop_tree


def save(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')


def omit_unused_vae(graph):
    """The pinned core only reads this optional VAE when reference images exist."""
    graph = copy.deepcopy(graph)
    known = {'clip', 'prompt', 'negative_prompt', 'resolution', 'vae'}
    for node in graph.values():
        if node['class_type'] == 'TextEncodeQwenImage21' and set(node['inputs']) <= known:
            node['inputs'].pop('vae', None)
    return graph


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--timeout', type=int, default=1200)
    parser.add_argument('--workflow', type=Path, nargs='+', required=True)
    parser.add_argument('--stack-hook', type=Path, help='Optional diagnostic sitecustomize directory')
    parser.add_argument('--free-check', choices=['reserved', 'active'], default='reserved',
                        help='Active permits cached allocator blocks; both metrics remain recorded')
    parser.add_argument('--host-trim', action='store_true',
                        help='Opt-in glibc unused-heap reclaim after /free; requires diagnostic stack hook')
    parser.add_argument('--decode-probe', action='store_true',
                        help='Only replay an existing saved-latent decode to measure host heap retention')
    parser.add_argument('--omit-unused-vae', action='store_true',
                        help='Avoid loading the optional VAE for text-only Qwen encoding')
    args = parser.parse_args()
    if args.host_trim and not args.stack_hook:
        parser.error('--host-trim requires --stack-hook')
    runtime = ROOT / 'runtime/ubuntu'
    out = args.out.resolve()
    base = 'http://127.0.0.1:8190'
    try:
        urlopen(base + '/system_stats', timeout=2)
    except OSError:
        pass
    else:
        parser.error('Port occupied; refusing to use another service')
    out.mkdir(parents=True, exist_ok=False)
    command = [str(runtime / '.venv/bin/python'), '-u', 'ComfyUI/main.py',
        '--listen', '127.0.0.1', '--port', '8190', '--cpu-vae', '--disable-async-offload',
        '--disable-dynamic-vram', '--fast-disk', '--reserve-vram', '1.0',
        '--use-split-cross-attention', '--force-fp16', '--force-upcast-attention',
        '--extra-model-paths-config', str(runtime / 'model-paths.yaml'),
        '--output-directory', str(out / 'images')]
    summary = {'status': 'running', 'command': command, 'same_process': True,
        'min_available_ram_mib': 1536, 'phases': [], 'images': [],
        'precision_change': 'Explicit FP16 with upcast attention; not equivalent to default FP32 casting'}
    summary['free_check'] = args.free_check
    summary['host_trim'] = args.host_trim
    summary['decode_probe_only'] = args.decode_probe
    summary['omit_unused_vae'] = args.omit_unused_vae
    summary['runner_sha256_at_startup'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    summary['runtime_source_sha256'] = {name: hashlib.sha256((runtime / name).read_bytes()).hexdigest()
        for name in ('ComfyUI/custom_nodes/ComfyUI-GGUF/nodes.py',
                     'ComfyUI/custom_nodes/ComfyUI-GGUF/ops.py', 'ComfyUI/comfy_extras/nodes_qwen.py',
                     'ComfyUI/custom_nodes/repair_conditioning/__init__.py', 'model-paths.yaml')}
    save(out / 'summary.json', summary)
    environment = os.environ.copy()
    environment['PYTHONFAULTHANDLER'] = '1'
    if args.stack_hook:
        environment['PYTHONPATH'] = str(args.stack_hook.resolve())
    with (out / 'server.stdout.log').open('wb') as stdout, (out / 'server.stderr.log').open('wb') as stderr:
        server = subprocess.Popen(command, cwd=runtime, stdout=stdout, stderr=stderr, env=environment)
    child = None
    summary['pid'] = server.pid

    def sample():
        if server.poll() is not None:
            raise RuntimeError(f'Owned server exited: {server.returncode}')
        available = psutil.virtual_memory().available
        with (out / 'memory.jsonl').open('a') as log:
            log.write(json.dumps({'time': time.time(), 'available_bytes': available,
                'server_rss': psutil.Process(server.pid).memory_info().rss}) + '\n')
        if available < 1536 * 1024**2:
            summary['operator_stop'] = 'physical_ram_guard'
            raise MemoryError('Physical RAM below 1536MiB; stopping owned service')

    def run_phase(label, graph):
        nonlocal child
        path = out / (label + '.api.json')
        save(path, graph)
        started = time.monotonic()
        phase = {'id': label, 'api_sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
        summary['phases'].append(phase)
        save(out / 'summary.json', summary)
        with (out / (label + '.log')).open('wb') as log:
            child = subprocess.Popen([sys.executable, str(ROOT / 'scripts/replay_workflow.py'),
                str(path), '--url', base, '--out', str(out / label), '--timeout', str(args.timeout)],
                stdout=log, stderr=subprocess.STDOUT)
        while child.poll() is None:
            sample()
            if time.monotonic() - started > args.timeout + 90:
                raise TimeoutError(label)
            time.sleep(1)
        phase.update({'exit_code': child.returncode, 'seconds': time.monotonic() - started})
        if child.returncode:
            raise RuntimeError(f'{label} failed; see retained history/logs')
        history = json.loads((out / label / 'history.json').read_text())
        entry = next(iter(history.values()))
        phase['prompt_id'] = next(iter(history))
        phase['history_sha256'] = hashlib.sha256((out / label / 'history.json').read_bytes()).hexdigest()
        def stats():
            with urlopen(base + '/system_stats', timeout=3) as response:
                return json.load(response)['devices']
        unload = {'before': stats(), 'samples': []}
        phase['explicit_unload'] = unload
        request = Request(base + '/free', data=b'{"unload_models":true,"free_memory":true}',
                          headers={'Content-Type': 'application/json'})
        with urlopen(request, timeout=3) as response:
            unload['http_status'] = response.status
        deadline = time.monotonic() + 60
        started_free = time.monotonic()
        traced = False
        while True:
            sample()
            devices = stats()
            unload['samples'].append({'seconds': time.monotonic() - started_free, 'devices': devices})
            save(out / 'summary.json', summary)
            gpu = [d for d in devices if d['type'] != 'cpu']
            reserved_ok = bool(gpu) and all(d['torch_vram_total'] <= 256 * 1024**2 for d in gpu)
            active_ok = bool(gpu) and all(d['torch_vram_total'] - d['torch_vram_free'] <= 256 * 1024**2 for d in gpu)
            unload['gpu_reserved_below_256_mib'] = reserved_ok
            unload['gpu_active_below_256_mib'] = active_ok
            if reserved_ok or (args.free_check == 'active' and active_ok):
                unload['meaning'] = 'Real /free; active-byte check allows retained allocator cache, not complete reserved-memory release or OOM recovery'
                break
            if args.stack_hook and not traced and time.monotonic() - started_free > 15:
                os.kill(server.pid, signal.SIGUSR1)
                traced = True
            if time.monotonic() > deadline:
                raise TimeoutError('Explicit /free did not reach 256MiB; see allocator samples')
            time.sleep(1)
        time.sleep(2)
        if args.host_trim:
            before = psutil.Process(server.pid).memory_info().rss
            os.kill(server.pid, signal.SIGUSR2)
            time.sleep(1)
            phase['host_heap_trim'] = {'before_rss': before,
                'after_rss': psutil.Process(server.pid).memory_info().rss,
                'meaning': 'Explicit gc + glibc malloc_trim; see server.stdout.log for allocator evidence'}
        sample()
        save(out / 'summary.json', summary)
        print('DONE', label, round(phase['seconds'], 2), flush=True)
        return entry

    def archive(entry, node):
        saved = entry['outputs'][node]
        relative, digest = saved['text'][0], saved['archive_sha256'][0]
        path = (runtime / 'ComfyUI/input' / relative).resolve()
        root = (runtime / 'ComfyUI/input/repair_conditioning').resolve()
        if not path.is_relative_to(root) or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError('Archive path or hash invalid')
        return relative, digest

    try:
        deadline = time.monotonic() + 120
        while True:
            sample()
            try:
                with urlopen(base + '/system_stats', timeout=2) as response:
                    summary['system_stats'] = json.load(response)
                break
            except OSError:
                if time.monotonic() > deadline:
                    raise TimeoutError('Startup')
                time.sleep(1)
        print('READY', server.pid, flush=True)
        for index, workflow in enumerate(args.workflow, 1):
            graph = json.loads(workflow.read_text())
            label = f'round-{index:02d}'
            if args.decode_probe:
                if not any(n['class_type'] == 'LoadRepairLatent' for n in graph.values()):
                    raise ValueError('Decode probe requires an existing archived latent')
                run_phase(label + '-decode-probe', graph)
                continue
            save(out / (label + '-original.json'), graph)
            digest = hashlib.sha256(workflow.read_bytes()).hexdigest()
            encode = copy.deepcopy(graph)
            encode['repair_save_conditions'] = {'class_type': 'SaveRepairConditioning', 'inputs': {
                'positive': graph['5']['inputs']['positive'], 'negative': graph['5']['inputs']['negative'],
                'latent': graph['5']['inputs']['latent_image'], 'prefix': label,
                'workflow_sha256': digest}}
            if args.omit_unused_vae:
                encode = omit_unused_vae(encode)
            entry = run_phase(label + '-encode', prune(encode, ['repair_save_conditions']))
            relative, archive_hash = archive(entry, 'repair_save_conditions')
            sampling = copy.deepcopy(graph)
            sampling['repair_load_conditions'] = {'class_type': 'LoadRepairConditioning', 'inputs': {
                'file': relative, 'expected_sha256': archive_hash}}
            for key, slot in (('positive', 0), ('negative', 1), ('latent_image', 2)):
                sampling['5']['inputs'][key] = ['repair_load_conditions', slot]
            entry = run_phase(label + '-sample', latent_sampling_graph(sampling, '5', label, digest))
            relative, archive_hash = archive(entry, 'repair_save_latent')
            entry = run_phase(label + '-decode', latent_decode_graph(graph, '5', ['7'], relative, archive_hash))
            for record in entry['outputs']['7']['images']:
                path = out / 'images' / record['subfolder'] / record['filename']
                summary['images'].append({'round': index, 'file': str(path.relative_to(out)),
                    'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'visual_verdict': 'pending'})
        summary['status'] = 'execution_pass_visual_review_pending'
    except (Exception, KeyboardInterrupt) as error:
        summary.update({'status': 'failed', 'error': str(error)})
        print('FAIL', error, flush=True)
    finally:
        if child is not None and child.poll() is None:
            stop_tree(child.pid)
        stop_tree(server.pid)
        server.wait(timeout=30)
        summary.update({'server_stopped': True, 'server_exit_code': server.returncode})
        save(out / 'summary.json', summary)
    return 0 if summary['status'] == 'execution_pass_visual_review_pending' else 1


if __name__ == '__main__':
    raise SystemExit(main())
