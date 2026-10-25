"""Observe only this verification job; keep the existing RAM guard boundary."""
import json
from pathlib import Path
import shutil
import time
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
BASE = 'http://127.0.0.1:8188'


def get(endpoint):
    return json.load(urlopen(BASE + endpoint, timeout=10))


deadline = time.monotonic() + 60
while not (HERE / 'webui-queue-receipt.json').exists():
    if time.monotonic() > deadline:
        raise TimeoutError('Frontend did not enqueue a prompt')
    time.sleep(1)
receipt = json.loads((HERE / 'webui-queue-receipt.json').read_text())
prompt_id = receipt['response']['prompt_id']
minimum = float('inf')
samples = []
deadline = time.monotonic() + 600
stopped = None
while time.monotonic() < deadline:
    memory = dict(line.split(':', 1) for line in Path('/proc/meminfo').read_text().splitlines())
    available = int(memory['MemAvailable'].strip().split()[0]) / 1024
    minimum = min(minimum, available)
    samples.append({'time': time.time(), 'available_ram_mib': available})
    history = get('/history/' + prompt_id)
    if prompt_id in history:
        history = history[prompt_id]
        (HERE / 'webui-history.json').write_text(json.dumps(history, ensure_ascii=False, indent=2) + '\n')
        break
    queue = get('/queue')
    owns_running = any(row[1] == prompt_id for row in queue['queue_running'])
    if available < 1536 and owns_running:
        urlopen(Request(BASE + '/interrupt', data=b'{}', headers={'Content-Type': 'application/json'}), timeout=10).close()
        stopped = 'operator RAM guard below 1536MiB; not a native OOM'
        break
    time.sleep(2)
else:
    stopped = 'observation timeout; inspect queue before any further action'
result = {'prompt_id': prompt_id, 'minimum_available_ram_mib': minimum, 'stopped': stopped,
          'source': receipt['source'], 'execution_status': history.get('status', {}) if isinstance(history, dict) else {}}
if not stopped:
    result['images'] = []
    for output in history.get('outputs', {}).values():
        for image in output.get('images', []):
            source = ROOT / 'runtime/ubuntu/ComfyUI/output' / image.get('subfolder', '') / image['filename']
            target = HERE / image['filename']
            shutil.copy2(source, target)
            result['images'].append(target.relative_to(ROOT).as_posix())
(HERE / 'webui-execution.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
(HERE / 'webui-memory.json').write_text(json.dumps(samples, indent=2) + '\n')
print(json.dumps(result, ensure_ascii=False))
