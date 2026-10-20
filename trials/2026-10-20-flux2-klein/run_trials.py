"""Run Flux.2 Klein trials with verified runtime and image-to-request binding."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import time

import psutil
import requests
from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
COMFY = ROOT / 'ComfyUI'
INPUTS = COMFY / 'input'
BASE = 'http://127.0.0.1:8188'
REQUIRED_FLAGS = (
    '--enable-dynamic-vram', '--fast-disk', '--disable-pinned-memory',
    '--cpu-vae', '--disable-async-offload', '--fp8_e4m3fn-text-enc',
)
POLL_SECONDS = 5
CASE_TIMEOUT_SECONDS = 2400


def save(path, value, *, exclusive=False):
    """Write a new evidence file without replacing evidence from an earlier run."""
    mode = 'x' if exclusive else 'w'
    with path.open(mode, encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())


def emit(*values):
    line = ' '.join(map(str, values))
    print(line, flush=True)
    with (HERE / 'runner.log').open('a', encoding='utf-8') as log:
        log.write(line + '\n')


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def graph_for(case):
    bindings = read_json(HERE / 'workflows/bindings.json')
    key = {'t2i': 't2i_512', 'single': 'single_edit_025mp',
           'dual': 'dual_edit_025mp'}[case['recipe']]
    binding = bindings['workflows'][key]
    graph = read_json(HERE / 'workflows' / binding['api_file'])
    graph[binding['prompt_node_id']]['inputs']['text'] = case['prompt']
    graph[binding['save_image_node_id']]['inputs']['filename_prefix'] = (
        'FeatureBench/' + case['id'])
    graph[binding['noise_node_id']]['inputs']['noise_seed'] = case.get(
        'seed', 665024001)
    if case.get('gpu_text'):
        for node in graph.values():
            if node['class_type'] == 'CLIPLoader':
                node['inputs']['device'] = 'default'
    for node, filename in zip(binding['load_image_nodes'], case['refs'], strict=True):
        input_path = (INPUTS / filename).resolve()
        if not input_path.is_relative_to(INPUTS.resolve()) or not input_path.is_file():
            raise FileNotFoundError(INPUTS / filename)
        graph[node['node_id']]['inputs']['image'] = filename
    if case.get('resolution'):
        for node in graph.values():
            if node['class_type'] in ('Flux2Scheduler', 'EmptyFlux2LatentImage'):
                node['inputs'].update(width=case['resolution'],
                                      height=case['resolution'])
    return graph


def normalized(value):
    if isinstance(value, dict):
        return {key: normalized(item) for key, item in value.items()
                if key != 'is_changed'}
    if isinstance(value, list):
        return [normalized(item) for item in value]
    return value


def graph_digest(graph):
    data = json.dumps(normalized(graph), ensure_ascii=False, sort_keys=True,
                      separators=(',', ':')).encode('utf-8')
    return hashlib.sha256(data).hexdigest()


def hash_file(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def input_records(case):
    records = []
    filenames = list(dict.fromkeys(case.get('inputs', []) + case.get('refs', [])))
    for filename in filenames:
        path = (INPUTS / filename).resolve()
        if not path.is_relative_to(INPUTS.resolve()) or not path.is_file():
            raise FileNotFoundError(INPUTS / filename)
        with Image.open(path) as image:
            dimensions = list(image.size)
        records.append({
            'declared_path': filename,
            'path': str(path),
            'bytes': path.stat().st_size,
            'dimensions': dimensions,
            'sha256': hash_file(path),
        })
    return records


def probe_time(value):
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=timezone.utc)
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.astimezone()
    return parsed.astimezone(timezone.utc)


def latest_fresh_probe(now=None):
    now = now or datetime.now(timezone.utc)
    candidates = []
    latest_directory = sorted((HERE / 'gpu-probes').iterdir())[-1]
    for path in [latest_directory / 'result.json']:
        try:
            result = read_json(path)
        except (OSError, json.JSONDecodeError):
            continue
        completed = probe_time(result.get('completed_at'))
        if (completed is None or not result.get('healthy')
                or result.get('returncode') != 0 or result.get('timed_out')):
            continue
        age = (now - completed).total_seconds()
        if 0 <= age < 300:
            candidates.append((completed, path, result, age))
    if not candidates:
        raise RuntimeError('No healthy GPU probe completed within the last 300 seconds')
    completed, path, result, age = max(candidates, key=lambda item: item[0])
    return {
        'path': str(path),
        'completed_at': result['completed_at'],
        'age_seconds': round(age, 2),
        'status': result.get('status'),
        'healthy': result.get('healthy'),
        'returncode': result.get('returncode'),
    }


def argv_values(argv):
    values = {}
    for index, value in enumerate(argv):
        if value.startswith('--') and index + 1 < len(argv):
            following = argv[index + 1]
            if not following.startswith('--'):
                values[value] = following
    return values


def expected_model_paths_config(argv):
    values = argv_values(argv)
    config_value = values.get('--extra-model-paths-config')
    if not config_value:
        raise RuntimeError('Missing --extra-model-paths-config in live server argv')
    supplied = Path(config_value)
    expected = (HERE / 'ssd-model-paths.yaml').resolve()
    candidates = [supplied]
    if not supplied.is_absolute():
        candidates.extend((ROOT / supplied, COMFY / supplied, HERE / supplied))
    for candidate in candidates:
        try:
            resolved = candidate.resolve(strict=True)
        except OSError:
            continue
        if resolved == expected and resolved.is_file():
            return {'argv_value': config_value, 'resolved_path': str(resolved),
                    'sha256': hash_file(resolved)}
    raise RuntimeError(
        f'Live argv model-path config does not resolve to {expected}: {config_value}')


def validate_dynamic_runtime(system_stats, probe, memory_profile='dynamic-nvme'):
    system = system_stats.get('system', {})
    argv = system.get('argv')
    if not isinstance(argv, list) or not all(isinstance(arg, str) for arg in argv):
        raise RuntimeError('/system_stats did not provide the live server argv')
    required_flags=tuple(flag for flag in REQUIRED_FLAGS if memory_profile!='dynamic-nvme-pinned' or flag!='--disable-pinned-memory')
    missing = [flag for flag in required_flags if flag not in argv]
    if memory_profile=='dynamic-nvme-pinned' and '--disable-pinned-memory' in argv:
        missing.append('forbidden --disable-pinned-memory for pinned comparison')
    missing.extend('forbidden '+flag for flag in (
        '--disable-dynamic-vram', '--disable-fast-disk', '--lowvram', '--cpu', '--gpu-only'
    ) if flag in argv)
    if missing:
        raise RuntimeError('Live server argv is missing required flags: ' + ', '.join(missing))
    values = argv_values(argv)
    reserve = values.get('--reserve-vram')
    if reserve is None:
        # Also accept a combined spelling if a future Comfy build exposes one.
        reserve = next((arg.removeprefix('--reserve-vram') for arg in argv
                        if arg.startswith('--reserve-vram')
                        and arg != '--reserve-vram'), None)
    try:
        if float(reserve) != 2.0:
            raise ValueError
    except (TypeError, ValueError):
        raise RuntimeError('Live server must reserve exactly 2 GiB of VRAM') from None
    config = expected_model_paths_config(argv)
    devices = system_stats.get('devices', [])
    gpu = next((device for device in devices
                if 'AMD Radeon RX 6650 XT' in str(device.get('name', ''))), None)
    if gpu is None:
        raise RuntimeError('/system_stats does not identify AMD Radeon RX 6650 XT')
    return {
        'verified': True,
        'memory_profile': memory_profile,
        'argv': argv,
        'required_flags': list(required_flags),
        'reserve_vram_gib': float(reserve),
        'model_paths_config': config,
        'gpu_device': gpu,
        'fresh_gpu_probe': probe,
    }


def check_dependency(case):
    dependency_id = case['depends_on']
    dep_folder = HERE / 'cases' / dependency_id
    result_path = dep_folder / 'result.json'
    if not result_path.is_file():
        raise RuntimeError(f'Missing dependency result: {result_path}')
    dependency = read_json(result_path)
    validation = dependency.get('binding_validation', {})
    if (dependency.get('status') != 'success'
            or not validation.get('passed')
            or not dependency.get('image_metadata')):
        raise RuntimeError('Dependency lacks a successful, image-bound result')
    reviews_path = HERE / 'reviews.json'
    if not reviews_path.is_file():
        raise RuntimeError('Iterative case requires reviews.json with verdict=通过')
    review = read_json(reviews_path).get(dependency_id, {})
    verdict = str(review.get('verdict', '')).strip().casefold()
    if verdict not in {'通过', 'pass', 'passed'}:
        raise RuntimeError(f'Iterative dependency review is not passed: {review.get("verdict")}')
    target = (INPUTS / case['refs'][0]).resolve()
    if not target.is_file():
        raise RuntimeError(f'Missing dependency image input: {target}')
    expected_hash = dependency['image_metadata'][0]['sha256']
    actual_hash = hash_file(target)
    if actual_hash != expected_hash:
        raise RuntimeError('Iterative input image hash differs from reviewed dependency output')
    return {'case_id': dependency_id, 'review': review,
            'input_path': str(target), 'sha256': actual_hash}


def save_api_if_safe(path, graph):
    if path.exists():
        if normalized(read_json(path)) != normalized(graph):
            raise RuntimeError(f'Existing API graph differs; preserving it: {path}')
        return
    save(path, graph, exclusive=True)


def terminal_status(history):
    value = history.get('status', {})
    status = value.get('status_str') if isinstance(value, dict) else None
    return status if status in {'success', 'error'} else None


def graph_from_history_prompt(value):
    if isinstance(value, list) and len(value) >= 3 and isinstance(value[2], dict):
        return value[2]
    if isinstance(value, dict):
        for key in ('prompt', 'graph', 'api'):
            if isinstance(value.get(key), dict):
                return value[key]
    return None


def output_records(case, history, submitted_graph, binding):
    outputs = history.get('outputs', {})
    save_id = binding['save_image_node_id']
    unexpected_nodes = [node for node, output in outputs.items()
                        if output.get('images') and node != save_id]
    save_output = outputs.get(save_id, {})
    items = save_output.get('images', [])
    if len(items) != 1 or unexpected_nodes:
        raise RuntimeError(
            f'Expected exactly one image from SaveImage node {save_id}; '
            f'got {len(items)} and unexpected nodes {unexpected_nodes}')
    item = items[0]
    output_root = COMFY.resolve()
    path = (COMFY / item.get('type', 'output') / item.get('subfolder', '')
            / item['filename']).resolve()
    if not path.is_relative_to(output_root) or not path.is_file():
        raise RuntimeError(f'History output image is missing or escapes ComfyUI: {path}')
    with Image.open(path) as image:
        dimensions = list(image.size)
        embedded_prompt = image.info.get('prompt')
    if isinstance(embedded_prompt, str):
        try:
            embedded_prompt = json.loads(embedded_prompt)
        except json.JSONDecodeError:
            embedded_prompt = None
    history_graph = graph_from_history_prompt(history.get('prompt'))
    api_graph_matches = (isinstance(embedded_prompt, dict)
                         and normalized(embedded_prompt) == normalized(submitted_graph))
    history_graph_matches = (isinstance(history_graph, dict)
                             and normalized(history_graph) == normalized(submitted_graph))
    explicit_prompt_matches = (
        submitted_graph[binding['prompt_node_id']]['inputs'].get('text') == case['prompt'])
    image_refs_match = all(
        submitted_graph[node['node_id']]['inputs'].get('image') == filename
        for node, filename in zip(binding['load_image_nodes'], case['refs'], strict=True))
    if not api_graph_matches or not history_graph_matches:
        raise RuntimeError('PNG prompt metadata or terminal history graph differs from submitted API graph')
    if not explicit_prompt_matches or not image_refs_match:
        raise RuntimeError('Submitted graph does not bind the declared prompt and reference images')
    return [{
        'path': str(path),
        'dimensions': dimensions,
        'bytes': path.stat().st_size,
        'sha256': hash_file(path),
        'png_prompt_graph_matches_api': api_graph_matches,
        'history_graph_matches_api': history_graph_matches,
        'prompt_matches_case': explicit_prompt_matches,
        'references_match_case': image_refs_match,
    }]


def append_resource_sample(path, sample):
    with path.open('a', encoding='utf-8', newline='\n') as stream:
        stream.write(json.dumps(sample, ensure_ascii=False) + '\n')
        stream.flush()


def resource_sample():
    memory = psutil.virtual_memory()
    sample = {
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'host_ram': {
            'total_bytes': memory.total,
            'available_bytes': memory.available,
            'used_bytes': memory.used,
            'percent': memory.percent,
        },
        'runner_process_rss_bytes': psutil.Process().memory_info().rss,
    }
    try:
        stats = requests.get(BASE + '/system_stats', timeout=10).json()
        sample['api_devices'] = [
            {key: device.get(key) for key in
             ('name', 'type', 'index', 'vram_total', 'vram_free', 'torch_vram_total',
              'torch_vram_free') if key in device}
            for device in stats.get('devices', [])]
    except Exception as error:  # Resource sampling must not interrupt a submitted job.
        sample['api_sample_error'] = str(error)
    return sample


def verify_inputs_unchanged(before, case):
    after = input_records(case)
    before_by_path = {record['declared_path']: record for record in before}
    after_by_path = {record['declared_path']: record for record in after}
    changed = [name for name, record in before_by_path.items()
               if name not in after_by_path
               or after_by_path[name]['sha256'] != record['sha256']]
    if changed:
        raise RuntimeError('Input files changed during the run: ' + ', '.join(changed))


def _run(case):
    folder = HERE / 'cases' / case['id']
    folder.mkdir(parents=True, exist_ok=True)
    result_path = folder / 'result.json'
    if result_path.exists():
        emit('SKIP recorded attempt', case['id'])
        return
    blocked_markers = ('submission-intent.json', 'submission.json', 'history.json')
    existing = [name for name in blocked_markers if (folder / name).exists()]
    if existing:
        raise RuntimeError(
            'Existing submission evidence without result; inspect before retry: '
            + ', '.join(existing))
    if case.get('memory_profile') not in ('dynamic-nvme','dynamic-nvme-pinned'):
        raise RuntimeError(
            f'Unverified memory_profile for new attempt {case["id"]}: '
            f'{case.get("memory_profile", "missing")}')
    dependency = check_dependency(case) if case.get('depends_on') else None
    graph = graph_for(case)
    bindings = read_json(HERE / 'workflows/bindings.json')
    workflow_key = {'t2i': 't2i_512', 'single': 'single_edit_025mp',
                    'dual': 'dual_edit_025mp'}[case['recipe']]
    binding = bindings['workflows'][workflow_key]
    api_path = folder / 'api.json'
    save_api_if_safe(api_path, graph)
    inputs = input_records(case)

    probe = latest_fresh_probe()
    stats_response = requests.get(BASE + '/system_stats', timeout=15)
    stats_response.raise_for_status()
    system_stats = stats_response.json()
    runtime = validate_dynamic_runtime(system_stats, probe, case['memory_profile'])
    stats_path = folder / 'actual-system-stats.json'
    save(stats_path, system_stats, exclusive=True)
    queue_response = requests.get(BASE + '/queue', timeout=15)
    queue_response.raise_for_status()
    queue = queue_response.json()
    running = queue.get('queue_running', [])
    pending = queue.get('queue_pending', [])
    if running or pending:
        raise RuntimeError(f'ComfyUI queue is not idle: running={len(running)}, pending={len(pending)}')

    preflight = {
        'case_id': case['id'],
        'checked_at': datetime.now(timezone.utc).isoformat(),
        'system_stats_file': str(stats_path),
        'runtime': runtime,
        'queue': {'running': running, 'pending': pending, 'idle': True},
        'inputs': inputs,
        'dependency': dependency,
        'api_sha256': graph_digest(graph),
    }
    save(folder / 'preflight.json', preflight, exclusive=True)
    sample_path = folder / 'resource-samples.jsonl'
    with sample_path.open('x', encoding='utf-8', newline='\n'):
        pass

    started = time.time()
    intent = {
        'case_id': case['id'],
        'created_at': datetime.now(timezone.utc).isoformat(),
        'api_sha256': graph_digest(graph),
        'inputs': inputs,
        'preflight_file': str(folder / 'preflight.json'),
        'runtime': runtime,
    }
    # Once this durable marker exists, an ambiguous POST is never replayed automatically.
    save(folder / 'submission-intent.json', intent, exclusive=True)
    result = {
        'case_id': case['id'],
        'id': case['id'],
        'model': case.get('model'),
        'feature': case.get('feature'),
        'status': 'runner_error',
        'started_at': started,
        'runtime_profile': f"实际API参数已核验：{case['memory_profile']}，G盘配置、动态VRAM/fast-disk、CPU VAE/同步卸载、预留2GiB、FP8文本编码；锁页内存参数见runtime_verification.argv；设备AMD RX6650XT。实际文本计算设备还需日志确认。",
        'runtime_verification': runtime,
        'preflight_file': str(folder / 'preflight.json'),
        'actual_system_stats_file': str(stats_path),
        'input_metadata': inputs,
        'review': 'pending',
    }
    try:
        response = requests.post(BASE + '/prompt', json={'prompt': graph}, timeout=60)
        submission = response.json()
        save(folder / 'submission.json', submission, exclusive=True)
        response.raise_for_status()
        prompt_id = submission.get('prompt_id')
        if not prompt_id:
            raise RuntimeError('POST /prompt returned no prompt_id; intent retained')
        result['prompt_id'] = prompt_id
        emit('SUBMITTED', case['id'], prompt_id)
        deadline = time.monotonic() + CASE_TIMEOUT_SECONDS
        history = None
        while time.monotonic() < deadline:
            append_resource_sample(sample_path, resource_sample())
            try:
                response = requests.get(BASE + '/history/' + prompt_id, timeout=30)
                response.raise_for_status()
                payload = response.json()
                history = payload.get(prompt_id)
            except requests.ReadTimeout:
                time.sleep(POLL_SECONDS)
                continue
            if history and terminal_status(history):
                save(folder / 'history.json', history, exclusive=True)
                result['execution_status'] = terminal_status(history)
                result['errors'] = [details for kind, details in
                                    history.get('status', {}).get('messages', [])
                                    if kind == 'execution_error']
                if result['execution_status'] != 'success':
                    result['status'] = result['execution_status']
                    result['error'] = 'ComfyUI reported terminal execution failure'
                else:
                    result['image_metadata'] = output_records(case, history, graph, binding)
                    result['images'] = [item['path'] for item in result['image_metadata']]
                    result['binding_validation'] = {
                        'passed': all(item['png_prompt_graph_matches_api']
                                      and item['history_graph_matches_api']
                                      and item['prompt_matches_case']
                                      and item['references_match_case']
                                      for item in result['image_metadata']),
                        'api_sha256': graph_digest(graph),
                        'image_count': len(result['image_metadata']),
                    }
                    verify_inputs_unchanged(inputs, case)
                    target = INPUTS / 'flux2-klein-bench' / (case['id'] + '.png')
                    if case['id'] == 'flux2-klein-single-color' or case.get('creates_iterative_input'):
                        source = Path(result['image_metadata'][0]['path'])
                        target.parent.mkdir(parents=True, exist_ok=True)
                        source_hash = result['image_metadata'][0]['sha256']
                        if target.exists():
                            if hash_file(target) != source_hash:
                                raise RuntimeError(
                                    f'Generated dependency input already differs: {target}')
                        else:
                            shutil.copy2(source, target)
                        result['derived_input'] = {
                            'path': str(target.resolve()), 'sha256': hash_file(target),
                            'matches_output': hash_file(target) == source_hash,
                        }
                    if not result['binding_validation']['passed']:
                        result['status'] = 'runner_error'
                        result['error'] = 'Image-to-API binding validation failed'
                    else:
                        result['status'] = 'success'
                break
            time.sleep(POLL_SECONDS)
        else:
            result['status'] = 'runner_error'
            result['error'] = (
                f'No terminal ComfyUI history after {CASE_TIMEOUT_SECONDS} seconds; '
                'no history.json was fabricated')
    except Exception as error:
        result['status'] = 'runner_error'
        result['error'] = f'{type(error).__name__}: {error}'
    result['elapsed_seconds'] = round(time.time() - started, 2)
    save(result_path, result, exclusive=True)
    emit('DONE', case['id'], result['status'], result['elapsed_seconds'])
    if result['status'] != 'success':
        raise RuntimeError('Stopped after failure; preserve this attempt before retry')


def run(case):
    """Persist preflight failures as runner_error without inventing Comfy history."""
    folder = HERE / 'cases' / case['id']
    folder.mkdir(parents=True, exist_ok=True)
    result_path = folder / 'result.json'
    if result_path.exists():
        emit('SKIP recorded attempt', case['id'])
        return
    started = time.time()
    try:
        _run(case)
    except Exception as error:
        if not result_path.exists():
            save(result_path, {
                'case_id': case['id'],
                'feature': case.get('feature'),
                'status': 'runner_error',
                'started_at': started,
                'elapsed_seconds': round(time.time() - started, 2),
                'error': f'{type(error).__name__}: {error}',
                'review': 'pending',
            }, exclusive=True)
            emit('DONE', case['id'], 'runner_error', round(time.time() - started, 2))
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--case')
    args = parser.parse_args()
    cases = read_json(HERE / 'cases.json')
    if args.case and not any(case['id'] == args.case for case in cases):
        parser.error(f'unknown case id: {args.case}')
    for case in cases:
        if args.case is None or args.case == case['id']:
            run(case)
