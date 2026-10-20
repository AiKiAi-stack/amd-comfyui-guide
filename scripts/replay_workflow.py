"""Submit a saved ComfyUI API graph, preserving a separate new run."""
import argparse
import hashlib
import json
import time
from pathlib import Path
from urllib.error import URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('workflow', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--url', default='http://127.0.0.1:8188')
    parser.add_argument('--timeout', type=int, default=3600)
    args = parser.parse_args()
    if urlparse(args.url).hostname not in ('127.0.0.1', 'localhost', '::1'):
        parser.error('This tutorial runner only submits to localhost.')
    graph = json.loads(args.workflow.read_text(encoding='utf-8-sig'))
    if 'prompt' in graph:
        graph = graph['prompt']
    if not graph or not all(isinstance(v, dict) and 'class_type' in v for v in graph.values()):
        parser.error('Expected an API prompt, not a UI workflow.')

    def request(path, payload=None):
        data = None if payload is None else json.dumps(payload).encode()
        req = Request(args.url.rstrip('/') + path, data=data, headers={'Content-Type': 'application/json'})
        with urlopen(req, timeout=60) as response:
            return response.read()

    nodes = json.loads(request('/object_info'))
    missing = sorted({n['class_type'] for n in graph.values()} - nodes.keys())
    if missing:
        raise SystemExit(f'Missing custom/core nodes: {missing}')
    args.out.mkdir(parents=True, exist_ok=False)

    def save(name, obj):
        (args.out / name).write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding='utf-8')

    save('api.json', graph)
    started = time.monotonic()
    submission = json.loads(request('/prompt', {'prompt': graph}))
    save('submission.json', submission)
    if submission.get('node_errors') or not submission.get('prompt_id'):
        raise SystemExit('Submission rejected; inspect submission.json')
    prompt_id = submission['prompt_id']
    print('SUBMITTED', prompt_id, flush=True)
    while time.monotonic() - started < args.timeout:
        try:
            history = json.loads(request('/history/' + prompt_id))
        except (URLError, TimeoutError, OSError) as error:
            save('runner-error.json', {'error': str(error), 'elapsed_seconds': time.monotonic() - started})
            raise SystemExit('Service unavailable; preserved run, inspect ComfyUI logs.')
        if prompt_id not in history:
            time.sleep(3)
            continue
        save('history.json', history)
        item = history[prompt_id]
        images = []
        for node_id, output in item.get('outputs', {}).items():
            for index, record in enumerate(output.get('images', [])):
                data = request('/view?' + urlencode(record))
                name = f'{node_id}-{index}-{Path(record["filename"]).name}'
                (args.out / name).write_bytes(data)
                images.append({'file': name, 'sha256': hashlib.sha256(data).hexdigest()})
        status = item.get('status', {}).get('status_str', 'unknown')
        save('result.json', {'status': status, 'elapsed_seconds': round(time.monotonic()-started, 3),
                            'images': images, 'visual_verdict': 'pending manual inspection'})
        print(status, args.out, 'Visual review is required.')
        if status != 'success':
            raise SystemExit(1)
        return
    save('runner-error.json', {'error': 'timeout', 'prompt_id': prompt_id})
    raise SystemExit('Timed out; task may still be queued/running. Inspect service before resubmitting.')


if __name__ == '__main__':
    main()
