"""Preserve the known preflight-only rejection; no generation was submitted."""
import json
import shutil
from pathlib import Path

HERE=Path(__file__).resolve().parent
folder=(HERE/'cases/flux2-klein-single-color').resolve()
assert folder.is_relative_to((HERE/'cases').resolve())
result=json.loads((folder/'result.json').read_text(encoding='utf-8'))
assert result['status']=='runner_error' and 'No healthy GPU probe completed' in result['error']
assert not any((folder/name).exists() for name in ['submission-intent.json','submission.json','history.json'])
archive=(folder/'attempts/000-preflight-stale-probe').resolve()
assert archive.is_relative_to(folder) and not archive.exists()
archive.mkdir(parents=True)
for filename in ['api.json','result.json']:
    source=(folder/filename).resolve()
    target=(archive/filename).resolve()
    assert source.is_relative_to(folder) and target.is_relative_to(archive) and source.is_file()
    shutil.move(str(source),str(target))
print('Archived preflight-only rejection. No API POST, prompt_id or image existed.')
