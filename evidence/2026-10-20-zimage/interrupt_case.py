"""Interrupt only this trial's verified sole running prompt, preserving evidence."""
import json
from datetime import datetime,timezone
from pathlib import Path
import requests

HERE=Path(__file__).resolve().parent
folder=HERE/'cases/zimage-gguf-photo'
submission=json.loads((folder/'submission.json').read_text(encoding='utf-8'))
queue=requests.get('http://127.0.0.1:8188/queue',timeout=15).json()
assert len(queue['queue_running'])==1 and not queue['queue_pending'], 'Only the owned sole running prompt may be interrupted'
assert queue['queue_running'][0][1]==submission['prompt_id'], 'Unexpected active prompt; do not interrupt'
record=dict(timestamp=datetime.now(timezone.utc).isoformat(),reason='CPU text encoding exceeded seven minutes before diffusion; preserve interrupted baseline and switch to an independent GPU-text case.',
            prompt_id=submission['prompt_id'],queue_before=queue)
response=requests.post('http://127.0.0.1:8188/interrupt',json={'prompt_id':submission['prompt_id']},timeout=15)
record.update(http_status=response.status_code,response=response.text)
(folder/'interruption-request.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
response.raise_for_status()
print('INTERRUPTION_REQUESTED',submission['prompt_id'])
