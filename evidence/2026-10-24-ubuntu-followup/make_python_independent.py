"""Copy the existing Python base, then repoint only the Linux venv configuration."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = Path(__file__).parent
VENV = (ROOT / 'runtime/ubuntu/.venv').resolve()
DESTINATION = Path.home() / '.local/share/barely-comfy/python-3.12.14-20261024'
CONFIG = VENV / 'pyvenv.cfg'
before = CONFIG.read_bytes()
home = next(line.split('=', 1)[1].strip() for line in before.decode().splitlines() if line.startswith('home ='))
source = Path(home).parent
if 'codex-runtimes' not in str(source) or DESTINATION.exists():
    raise RuntimeError('Expected original app-cache Python and a fresh owned destination')
backup = EVIDENCE / 'pyvenv.before-independent.cfg'
if backup.exists():
    raise FileExistsError(backup)

probe = '''import json, sys, ssl, sqlite3, lzma, bz2, zlib, importlib.metadata
print(json.dumps({'base_prefix': sys.base_prefix, 'prefix': sys.prefix,
 'executable': sys.executable, 'ssl_module': ssl.__file__, 'sys_path': sys.path,
 'packages': {d.metadata['Name']: d.version for d in importlib.metadata.distributions()}}))'''


def check(python):
    return json.loads(subprocess.check_output([str(python), '-I', '-c', probe], text=True))


baseline = check(VENV / 'bin/python')
shutil.copytree(source, DESTINATION, symlinks=True, ignore=shutil.ignore_patterns('__pycache__'))
for path in DESTINATION.rglob('*'):
    if path.is_symlink():
        target = os.readlink(path)
        if target.startswith(str(source) + '/'):
            path.unlink()
            path.symlink_to(str(DESTINATION) + target[len(str(source)):])
standalone = check(DESTINATION / 'bin/python3')
if Path(standalone['base_prefix']) != DESTINATION:
    raise RuntimeError('Copied interpreter did not relocate')
backup.write_bytes(before)
temporary = CONFIG.with_name('pyvenv.cfg.followup-tmp')
with temporary.open('xb') as stream:
    stream.write(before.replace(str(source).encode(), str(DESTINATION).encode()))
os.replace(temporary, CONFIG)
try:
    after = check(VENV / 'bin/python')
    assert Path(after['base_prefix']) == DESTINATION
    assert after['packages'] == baseline['packages']
    assert all('codex-runtimes' not in p for p in after['sys_path'])
except Exception:
    CONFIG.write_bytes(before)
    raise
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
record = {'source_retained': str(source), 'owned_python': str(DESTINATION),
    'venv': str(VENV), 'config_backup': str(backup),
    'base_binary_sha256': sha(source / 'bin/python3.12'),
    'owned_binary_sha256': sha(DESTINATION / 'bin/python3.12'),
    'before': baseline, 'after': after, 'same_packages': True,
    'stdlib_probe': 'ssl/sqlite3/lzma/bz2/zlib imported successfully from relocated base',
    'rollback': 'Copy the saved cfg back; original Python base was retained'}
(EVIDENCE / 'independent-python.json').write_text(json.dumps(record, indent=2) + '\n')
print('Independent Python verified; unchanged distributions:', len(after['packages']))
