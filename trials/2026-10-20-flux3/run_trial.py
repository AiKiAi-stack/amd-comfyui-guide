"""Reproducible standard FLUX3 trials; never identifies these weights as UN."""
import argparse
import hashlib
import json
from pathlib import Path
import time

import requests

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BASE = 'http://127.0.0.1:8188'


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def convert(name):
    ui = json.loads((HERE / 'source_workflows' / name).read_text(encoding='utf-8'))
    links = {link[0]: [str(link[1]), link[2]] for link in ui['links']}
    graph = {}
    for node in ui['nodes']:
        inputs = {}
        named = node.get('widgets_values_named', {})
        for item in node.get('inputs', []):
            if item.get('link') is not None:
                inputs[item['name']] = links[item['link']]
            elif item['name'] in named and item['name'] != 'upload':
                inputs[item['name']] = named[item['name']]
        graph[str(node['id'])] = {'class_type': node['type'], 'inputs': inputs}
    graph['2']['inputs']['device'] = 'cpu'
    return graph


def graph_for(case):
    edit = case['recipe'] == 'reference'
    graph = convert('Image_EDIT_Flux3-Klein.json' if edit else 'Image_T2I_Flux3-Klein.json')
    latent, sampler, prompt, output = ('14', '7', '4', '9') if edit else ('7', '8', '5', '10')
    graph[latent]['inputs'].update(width=512, height=512, batch_size=1)
    graph[sampler]['inputs']['seed'] = case.get('seed', 66506001)
    graph[prompt]['inputs']['text'] = case['prompt']
    graph[output]['inputs']['filename_prefix'] = 'FeatureBench/' + case['id']
    if edit:
        graph['11']['inputs']['image'] = case['refs'][0]
        graph['12']['inputs'].update(megapixels=0.25, resolution_steps=16)
    return graph


def run(case):
    folder = HERE / 'cases' / case['id']
    folder.mkdir(parents=True, exist_ok=True)
    if (folder / 'result.json').exists():
        raise RuntimeError('Refusing to overwrite an existing attempt')
    graph = graph_for(case)
    save(folder / 'api.json', graph)
    started = time.time()
    result = {**case, 'started_at': started, 'review': 'pending', 'configuration':
              '512px; CPU text encoder + CPU VAE; GPU diffusion; gfx1032 INT8 emulation opt-in; standard Klein, not author UN'}
    try:
        response = requests.post(BASE + '/prompt', json={'prompt': graph}, timeout=60)
        submission = response.json()
        save(folder / 'submission.json', submission)
        response.raise_for_status()
        prompt_id = submission['prompt_id']
        result['prompt_id'] = prompt_id
        print('SUBMITTED', case['id'], prompt_id, flush=True)
        while time.time() - started < 3600:
            history = requests.get(BASE + '/history/' + prompt_id, timeout=30).json().get(prompt_id)
            if history:
                save(folder / 'history.json', history)
                result['status'] = history['status']['status_str']
                result['images'] = []
                result['image_checksums'] = {}
                for output in history.get('outputs', {}).values():
                    for image in output.get('images', []):
                        path = ROOT / 'ComfyUI' / image.get('type', 'output') / image.get('subfolder', '') / image['filename']
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
    save(folder / 'result.json', result)
    print('DONE', case['id'], result['status'], result['elapsed_seconds'], flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('case')
    args = parser.parse_args()
    cases = json.loads((HERE / 'cases.json').read_text(encoding='utf-8'))
    run(next(case for case in cases if case['id'] == args.case))
