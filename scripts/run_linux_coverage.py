"""Run separately recorded Ubuntu feature cases on an owned, RAM-guarded service."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import psutil
from PIL import Image

from platform_catalog import ROOT, linked, sha
from run_conditioned_repair import prune, conditioning_node

TRIAL = ROOT / 'evidence/2026-10-24-linux-coverage'
RUNTIME = ROOT / 'runtime/ubuntu'
RAW = ROOT / 'runs/linux-coverage-20261024'


def write_result(path, result):
    temporary = path.with_name(path.name + '.' + str(os.getpid()) + '.tmp')
    temporary.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    temporary.replace(path)


def request(route, data=None, timeout=10):
    body = None if data is None else json.dumps(data).encode()
    with urlopen(Request('http://127.0.0.1:8190' + route, data=body,
                         headers={'Content-Type': 'application/json'}), timeout=timeout) as response:
        return response.read()


def profile(model):
    args = ['--reserve-vram', '1.0', '--use-split-cross-attention']
    if model in ('qwen-base', 'qwen-turbo', 'kroma', 'moss'):
        args += ['--force-fp16', '--force-upcast-attention']
    if model == 'flux2':
        args += ['--fp8_e4m3fn-text-enc']
    return args


def prepare():
    if (TRIAL / 'plan.json').exists():
        print('Existing dated plan retained; completed evidence is not replaced', flush=True)
        return json.loads((TRIAL / 'plan.json').read_text())
    catalog = json.loads((ROOT / 'workflows/catalog.json').read_text())
    old_records = {r['id']: r for r in catalog['records']}
    covered = {(r['model_id'], r['feature_id']) for r in catalog['records'] if r['platform'] == 'Linux' and r['images']}
    selected = {}
    preferred = {'qwen-turbo:t2i': 'turbo-un-t2i', 'flux2:t2i': 'flux2-klein-t2i-gpu-text',
                 'qwen-base:caption': 'qwen-caption-gpu-chunked'}
    for job in catalog['workflows']:
        pair = (job['model_id'], job['feature_id'])
        if job['platform'] != 'Windows' or pair in covered or not job.get('frontend_import', {}).get('pass'):
            continue
        key = ':'.join(pair)
        if key not in selected or job['case_id'] == preferred.get(key):
            selected[key] = job
    plan = []
    for key, job in selected.items():
        graph = json.loads((ROOT / job['api']).read_text())
        changes = ['保存前缀改到本轮独立目录；原 Windows 图与评价不改']
        if job['model_id'] in ('qwen-base', 'qwen-turbo'):
            clip_ids = [k for k, n in graph.items() if n['class_type'] in ('CLIPLoader', 'CLIPLoaderGGUF')]
            for cid in clip_ids:
                original = copy.deepcopy(graph[cid])
                graph[cid] = {'class_type': 'CLIPLoaderGGUF', 'inputs': {
                    'clip_name': 'Qwen-Image-2.1-Turbo-Uncensored-Q4_K.gguf', 'type': 'qwen_image'}}
                if graph[cid] != original:
                    changes.append('Linux 编码器采用 UN GGUF Q4_K，区别于原 Windows INT8/普通编码器；扩散权重不变')
                wrapper = 'linux_clip_backing_' + cid
                for node in graph.values():
                    for name, value in node['inputs'].items():
                        if value == [cid, 0]: node['inputs'][name] = [wrapper, 0]
                graph[wrapper] = {'class_type': 'RetainGgufClipCpuBacking', 'inputs': {'clip': [cid, 0]}}
            changes.append('实例级 GGUF CLIP CPU backing v4，FP16/upcast；不据此宣称原 Windows 配方已在 Linux 执行')
            for node in graph.values():
                if node['class_type'] == 'TextEncodeQwenImage21' and not any(name.startswith('images.') for name in node['inputs']):
                    node['inputs'].pop('vae', None)
        for node in graph.values():
            if node['class_type'] == 'SaveImage':
                node['inputs']['filename_prefix'] = 'linux-coverage/' + job['case_id']
        case_dir = TRIAL / 'cases' / job['case_id']
        case_dir.mkdir(parents=True, exist_ok=True)
        target = case_dir / 'workflow.api.json'
        target.write_text(json.dumps(graph, ensure_ascii=False, indent=2) + '\n')
        plan.append({'id': 'linux-coverage-' + job['case_id'], 'case_id': job['case_id'],
                     'model_id': job['model_id'], 'feature_id': job['feature_id'], 'source': job['api'],
                     'source_sha256': sha(ROOT / job['api']), 'workflow': target.relative_to(ROOT).as_posix(),
                     'workflow_sha256': sha(target), 'changes': changes,
                     'profile_args': profile(job['model_id']), 'original_record': old_records[job['id']]})
    order = {'kroma': 0, 'flux2': 1, 'zimage-gguf': 2, 'zimage-aio': 3, 'moss': 4, 'qwen-turbo': 5, 'qwen-base': 6}
    plan.sort(key=lambda case: (order[case['model_id']], case['feature_id'] == 'caption', case['feature_id'] == 't2i-1024'))
    (TRIAL / 'plan.json').write_text(json.dumps(plan, ensure_ascii=False, indent=2) + '\n')
    print('PREPARED', len(plan), flush=True)
    return plan


def execute(case, timeout, diagnostic=False):
    folder = TRIAL / 'cases' / case['case_id']
    if (folder / 'execution.json').exists():
        previous = json.loads((folder / 'execution.json').read_text())
        if previous.get('workflow_sha256') != sha(ROOT / case['workflow']):
            raise ValueError('Existing result belongs to a different graph; use a new case ID')
        if previous['status'] != 'controller_error': return previous
        archived = folder / ('execution.controller-' + str(time.time_ns()) + '.json')
        (folder / 'execution.json').rename(archived)
    run = RAW / case['case_id'] / ('attempt-' + str(time.time_ns()))
    run.mkdir(parents=True, exist_ok=False)
    graph = json.loads((ROOT / case['workflow']).read_text())
    command = [str(RUNTIME / '.venv/bin/python'), '-u', 'ComfyUI/main.py', '--listen', '127.0.0.1',
               '--port', '8190', '--cpu-vae', '--disable-async-offload', '--disable-dynamic-vram',
               '--fast-disk', '--extra-model-paths-config', str(RUNTIME / 'model-paths.yaml'), *case['profile_args']]
    env = os.environ.copy()
    env.update({'COMFY_GFX1032_INT8_FALLBACK': '1', 'BARELY_COMFY_CHUNKED_GPU_LOGITS': '1',
                'BARELY_COMFY_CHUNKED_CPU_LOGITS': '1', 'PYTHONFAULTHANDLER': '1',
                'OPENBLAS_NUM_THREADS': '2', 'OMP_NUM_THREADS': '4'})
    if diagnostic:
        env['PYTHONPATH'] = str(TRIAL / 'diagnostics') + os.pathsep + env.get('PYTHONPATH', '')
    result = {'case_id': case['case_id'], 'command': command, 'environment': {k: env[k] for k in
              ('COMFY_GFX1032_INT8_FALLBACK', 'BARELY_COMFY_CHUNKED_CPU_LOGITS', 'BARELY_COMFY_CHUNKED_GPU_LOGITS', 'OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS')},
              'status': 'starting', 'images': [], 'workflow_sha256': sha(ROOT / case['workflow'])}
    log = (run / 'server.log').open('wb')
    server = subprocess.Popen(command, cwd=RUNTIME, env=env, stdout=log, stderr=log, start_new_session=True)
    log.close()
    result['pid'] = server.pid
    started = time.monotonic()
    minimum = psutil.virtual_memory().available / 1024**2
    queued = None
    try:
        while time.monotonic() - started < 90:
            if server.poll() is not None: raise RuntimeError('Startup exit ' + str(server.returncode))
            try:
                json.loads(request('/system_stats', timeout=2))
                break
            except (URLError, TimeoutError): time.sleep(1)
        else: raise TimeoutError('Startup timeout')
        definitions = request('/object_info', timeout=15)
        snapshot = RUNTIME / ('object-info-' + str(os.getpid()) + '.tmp')
        snapshot.write_bytes(definitions)
        snapshot.replace(RUNTIME / 'object-info-after-keke.json')
        submission = json.loads(request('/prompt', {'prompt': graph}, timeout=30))
        (folder / 'submission.json').write_text(json.dumps(submission, indent=2) + '\n')
        queued = time.monotonic()
        prompt = submission['prompt_id']
        result['prompt_id'] = prompt
        result['validation_errors'] = submission.get('node_errors', {})
        print('RUN', case['case_id'], prompt, flush=True)
        with (run / 'memory.jsonl').open('w') as memory:
            while time.monotonic() - queued < timeout:
                available = psutil.virtual_memory().available / 1024**2
                minimum = min(minimum, available)
                memory.write(json.dumps({'time': time.time(), 'available_mib': available}) + '\n');memory.flush()
                if available < 1536:
                    result['status'] = 'operator_ram_guard'
                    result['error'] = 'Available physical RAM below 1536MiB; operator stop, not native OOM'
                    break
                if server.poll() is not None: raise RuntimeError('Server exit ' + str(server.returncode))
                try:
                    history = json.loads(request('/history/' + prompt, timeout=5))
                except (TimeoutError, URLError, OSError):
                    if server.poll() is not None: raise RuntimeError('Server exit during poll: ' + str(server.returncode))
                    continue
                if prompt in history:
                    entry = history[prompt]
                    (folder / 'history.json').write_text(json.dumps(history, ensure_ascii=False, indent=2) + '\n')
                    result['status'] = entry.get('status', {}).get('status_str', 'unknown')
                    result['outputs'] = entry.get('outputs', {})
                    result['messages'] = entry.get('status', {}).get('messages', [])
                    for node_id, output in entry.get('outputs', {}).items():
                        for index, image in enumerate(output.get('images', [])):
                            data = request('/view?' + urlencode(image), timeout=30)
                            original = run / (str(node_id) + '-' + str(index) + '.png');original.write_bytes(data)
                            public = folder / original.name
                            with Image.open(original) as decoded:
                                rgb = decoded.convert('RGB'); pixels = rgb.tobytes()
                                Image.frombytes('RGB', rgb.size, pixels).save(public)
                                size = list(rgb.size)
                            result['images'].append({'file': public.name, 'size': size, 'sha256': sha(public),
                                                     'original_sha256': sha(original), 'rgb_sha256': hashlib.sha256(pixels).hexdigest()})
                    break
                time.sleep(2)
            else:
                result.update(status='operator_timeout', error='Observation timeout; owned server stopped')
    except HTTPError as error:
        result.update(status='submission_error', error=error.read().decode(errors='replace'))
    except (Exception, KeyboardInterrupt) as error:
        result.update(status='controller_error', error=str(error))
    finally:
        if server.poll() is None:
            os.killpg(server.pid, signal.SIGTERM)
            try: server.wait(timeout=10)
            except subprocess.TimeoutExpired: os.killpg(server.pid, signal.SIGKILL);server.wait(timeout=10)
        result['minimum_available_ram_mib'] = minimum
        result['elapsed_seconds'] = round(time.monotonic() - (queued or started), 3)
        result['total_seconds'] = round(time.monotonic() - started, 3)
        result['server_exit'] = server.returncode
        write_result(folder / 'execution.json', result)
    print('DONE', case['case_id'], result['status'], len(result['images']), result['elapsed_seconds'], flush=True)
    return result


def execute_staged(case, timeout):
    """Preserve exact conditioning across fresh processes; no unload-fix claim."""
    if case.get('execution_mode') == 'caption-three-phase':
        from run_linux_caption_staged import execute_caption_staged
        return execute_caption_staged(case, timeout, execute, write_result)
    folder = TRIAL / 'cases' / case['case_id']
    previous_path = folder / 'execution.json'
    if previous_path.exists():
        previous = json.loads(previous_path.read_text())
        if previous['status'] == 'success' and previous['images']: return previous
        previous_path.rename(folder / ('execution.whole-' + str(time.time_ns()) + '.json'))
    graph = json.loads((ROOT / case['workflow']).read_text())
    samplers = [k for k,n in graph.items() if n['class_type'] in ('KSampler', 'SamplerCustomAdvanced')]
    if len(samplers) != 1: raise ValueError('Staged execution requires exactly one sampler')
    sampler = samplers[0]; conditioner = conditioning_node(graph, sampler)
    output_ids = [k for k,n in graph.items() if n['class_type'] == 'SaveImage']
    encoded = copy.deepcopy(graph)
    encoded['repair_save_conditions'] = {'class_type': 'SaveRepairConditioning', 'inputs': {
        'positive': graph[conditioner]['inputs']['positive'], 'negative': graph[conditioner]['inputs']['negative'],
        'latent': graph[sampler]['inputs']['latent_image'], 'prefix': 'linux-coverage-' + case['case_id'],
        'workflow_sha256': sha(ROOT / case['workflow'])}}
    encoded = prune(encoded, ['repair_save_conditions'])

    def phase(name, phase_graph):
        item = copy.deepcopy(case);item['case_id'] += '--' + name
        item['profile_args'] = case.get('phase_profile_args', {}).get(name, case['profile_args'])
        directory = TRIAL / 'cases' / item['case_id'];directory.mkdir(exist_ok=True)
        path = directory / 'workflow.api.json'
        content = json.dumps(phase_graph, ensure_ascii=False, indent=2)+'\n'
        if path.exists() and path.read_text() != content:
            raise ValueError('Refusing to replace an existing phase graph; use a new case ID')
        if not path.exists(): path.write_text(content)
        item['workflow'] = path.relative_to(ROOT).as_posix()
        return execute(item, timeout)

    first = phase('encode', encoded)
    if first['status'] != 'success':
        first = copy.deepcopy(first);first.update(case_id=case['case_id'], staged=True, failed_phase='encoding')
        first['encoding_workflow_sha256'] = first['workflow_sha256']
        first['workflow_sha256'] = sha(ROOT / case['workflow'])
        write_result(previous_path, first);return first
    saved = first['outputs']['repair_save_conditions']
    relative, digest = saved['text'][0], saved['archive_sha256'][0]
    archive = (RUNTIME / 'ComfyUI/input' / relative).resolve()
    if not archive.is_relative_to((RUNTIME / 'ComfyUI/input/repair_conditioning').resolve()) or sha(archive) != digest:
        raise ValueError('Conditioning archive path/hash mismatch')
    sampled = copy.deepcopy(graph)
    sampled['repair_load_conditions'] = {'class_type':'LoadRepairConditioning','inputs':{'file':relative,'expected_sha256':digest}}
    for name,slot in [('positive',0),('negative',1)]:sampled[conditioner]['inputs'][name]=['repair_load_conditions',slot]
    sampled[sampler]['inputs']['latent_image']=['repair_load_conditions',2]
    sampled = prune(sampled,output_ids)
    second = phase('sample',sampled)
    result = copy.deepcopy(second)
    result.update(case_id=case['case_id'],staged=True,encoding_seconds=first['elapsed_seconds'],
                  encoding_command=first['command'],encoding_environment=first['environment'],
                  sampling_seconds=second['elapsed_seconds'],elapsed_seconds=first['elapsed_seconds']+second['elapsed_seconds'],
                  total_seconds=first['total_seconds']+second['total_seconds'],
                  minimum_available_ram_mib=min(first['minimum_available_ram_mib'],second['minimum_available_ram_mib']),
                  conditioning_archive=relative,conditioning_sha256=digest,encoding_pid=first['pid'],sampling_pid=second['pid'],
                  encoding_exited_before_sampling=True,workflow_sha256=sha(ROOT/case['workflow']))
    for image in result['images']:
        image['file']='../'+case['case_id']+'--sample/'+image['file']
    write_result(previous_path, result)
    print('STAGED_DONE',case['case_id'],result['status'],len(result['images']),flush=True)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare', action='store_true')
    parser.add_argument('--models', nargs='*')
    parser.add_argument('--cases', nargs='*')
    parser.add_argument('--stack-diagnostic', action='store_true')
    parser.add_argument('--staged', action='store_true')
    parser.add_argument('--pending-only', action='store_true', help='Keep completed success/error/operator-stop evidence; resume only missing results or controller errors')
    parser.add_argument('--auto', action='store_true', help='Use the established Kroma staged workaround; stage other resource-stopped graphs once')
    parser.add_argument('--timeout', type=int, default=600)
    args = parser.parse_args()
    TRIAL.mkdir(exist_ok=True);RAW.mkdir(exist_ok=True)
    plan = prepare() if args.prepare or not (TRIAL / 'plan.json').exists() else json.loads((TRIAL / 'plan.json').read_text())
    if args.prepare: return
    try: request('/system_stats', timeout=2)
    except URLError: pass
    else: raise RuntimeError('Port 8190 is in use; refusing to interfere')
    for case in plan:
        if case.get('superseded_by'): continue
        if args.models and case['model_id'] not in args.models: continue
        if args.cases and case['case_id'] not in args.cases: continue
        previous = TRIAL / 'cases' / case['case_id'] / 'execution.json'
        if args.pending_only and previous.exists() and json.loads(previous.read_text()).get('status') != 'controller_error': continue
        if args.staged or case.get('execution_mode') == 'caption-three-phase' or (args.auto and case['model_id'] == 'kroma'):
            execute_staged(case, args.timeout)
        else:
            result = execute(case, args.timeout, args.stack_diagnostic)
            if args.auto and result['status'] in ('operator_ram_guard', 'operator_timeout', 'controller_error'):
                execute_staged(case, args.timeout)


if __name__ == '__main__':
    main()
