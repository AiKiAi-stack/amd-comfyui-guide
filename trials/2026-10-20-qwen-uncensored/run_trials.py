"""Local base Qwen-Image 2.1 + existing UN encoder; records every submitted graph."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

import requests

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BASE = 'http://127.0.0.1:8188'


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def graph_for(case):
    template = ROOT / 'trials/2026-10-19-features/cases/turbo-un-t2i/api.json'
    graph = json.loads(template.read_text(encoding='utf-8'))
    graph['1']['inputs']['unet_name'] = 'qwen-image-2.1-Q4_K_M.gguf'
    graph['4']['inputs'].update(prompt=case['prompt'], negative_prompt='', resolution=512)
    # Keep the known stable UN CPU encoder/cache-off configuration; swap only
    # the base diffusion checkpoint and its Euler/simple sampling schedule.
    for key in ('60', '61', '62', '63', '64'):
        del graph[key]
    graph['5'] = {'class_type': 'KSampler', 'inputs': {
        'model': ['81', 0], 'positive': ['4', 0], 'negative': ['4', 1],
        'latent_image': ['4', 2], 'seed': 210665042, 'steps': 15,
        'cfg': 1.0, 'sampler_name': 'euler', 'scheduler': 'simple', 'denoise': 1.0}}
    graph['6']['inputs']['samples'] = ['5', 0]
    graph['7']['inputs']['filename_prefix'] = 'UncensoredBench/' + case['id']
    return graph


def run(case):
    folder = HERE / 'cases' / case['id']
    folder.mkdir(parents=True, exist_ok=True)
    result_path = folder / 'result.json'
    if result_path.exists():
        print('SKIP', case['id'], flush=True)
        return
    if (folder / 'submission.json').exists():
        raise RuntimeError('Existing submission without result; reconcile history before resubmitting')
    graph = graph_for(case)
    save(folder / 'api.json', graph)
    started = time.time()
    result = {**case, 'model': 'Qwen-Image-2.1 base Q4_K_M + AtomicChat UN AD-Q4_K encoder',
              'started_at': started, 'review': 'pending',
              'configuration': 'CPU text/VAE, RX6650XT diffusion; 512px, 15 steps, Euler/simple CFG1; QwenImage21 cache off; no prompt enhancer; no negative prompt',
              'limitations': 'One seed, no stock-encoder control, reduced step count; cannot establish an uncensoring effect'}
    try:
        response = requests.post(BASE + '/prompt', json={'prompt': graph}, timeout=60)
        submission = response.json()
        save(folder / 'submission.json', submission)
        response.raise_for_status()
        prompt_id = submission['prompt_id']
        result['prompt_id'] = prompt_id
        print('SUBMITTED', case['id'], prompt_id, flush=True)
        deadline = time.monotonic() + 3600
        while time.monotonic() < deadline:
            try:
                history = requests.get(BASE + '/history/' + prompt_id, timeout=30).json().get(prompt_id)
            except requests.ReadTimeout:
                continue
            if history:
                save(folder / 'history.json', history)
                result['status'] = history['status']['status_str']
                result['images'] = []
                result['image_checksums'] = {}
                for output in history.get('outputs', {}).values():
                    for item in output.get('images', []):
                        path = ROOT / 'ComfyUI' / item.get('type', 'output') / item.get('subfolder', '') / item['filename']
                        result['images'].append(str(path))
                        result['image_checksums'][str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
                result['errors'] = [details for kind, details in history['status'].get('messages', []) if kind == 'execution_error']
                break
            time.sleep(5)
        else:
            result['status'] = 'timeout'
    except Exception as error:
        result.update(status='runner_error', error=str(error))
    result['elapsed_seconds'] = round(time.time() - started, 2)
    save(result_path, result)
    print('DONE', case['id'], result['status'], result['elapsed_seconds'], flush=True)
    if result['status'] != 'success':
        raise RuntimeError('Stopped after failed attempt; inspect evidence before retry')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--case')
    parser.add_argument('--fresh-server', action='store_true')
    args = parser.parse_args()
    cases = json.loads((HERE / 'cases.json').read_text(encoding='utf-8'))
    for case in cases:
        if args.case is None or args.case == case['id']:
            if (HERE / 'cases' / case['id'] / 'result.json').exists():
                print('SKIP', case['id'], flush=True)
                continue
            if args.fresh_server:
                sys.path.insert(0, str(ROOT / 'trials/2026-10-19-features'))
                import manage_server
                manage_server.restart('qwen-uncensored-prompts', cpu_text=True)
            run(case)
