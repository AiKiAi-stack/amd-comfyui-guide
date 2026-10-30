"""Install only round-trip checked UI files into a separate ComfyUI folder."""
import hashlib
import json
from pathlib import Path
import shutil
import time
from zipfile import ZipFile, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]


def write_bundle_status(catalog_bytes, installed_count):
    library = ROOT / 'workflows'
    bundles = []
    for name in ('model-feature-workflows.zip', 'model-feature-workflows-light.zip'):
        path = library / name
        digest = hashlib.sha256()
        with path.open('rb') as source:
            for chunk in iter(lambda: source.read(8 * 1024**2), b''): digest.update(chunk)
        bundles.append({'file': name, 'bytes': path.stat().st_size, 'sha256': digest.hexdigest()})
    status = {'time': time.time(), 'catalog_sha256': hashlib.sha256(catalog_bytes).hexdigest(),
              'installed_ui': installed_count, 'bundles': bundles}
    target = library / 'bundle-status.json'
    temporary = target.with_suffix('.tmp')
    temporary.write_text(json.dumps(status, indent=2) + '\n');temporary.replace(target)
    return status


def install():
    library = ROOT / 'workflows'
    catalog_bytes = (library / 'catalog.json').read_bytes()
    catalog = json.loads(catalog_bytes)
    destination = ROOT / 'runtime/ubuntu/ComfyUI/user/default/workflows' / catalog['runtime_prefix']
    receipt_path = ROOT / 'evidence/2026-10-24-platform-report/installation.json'
    previous = json.loads(receipt_path.read_text()) if receipt_path.exists() else {}
    owned = {r['installed']: r['sha256'] for r in previous.get('installed', [])}
    receipt = []
    for job in catalog['workflows']:
        if not job.get('frontend_import', {}).get('pass'):
            continue
        if not job.get('install_recommended', True):
            continue
        source = ROOT / job['ui']
        target = destination / source.relative_to(library / 'ui')
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        if target.exists():
            existing = hashlib.sha256(target.read_bytes()).hexdigest()
            if existing != digest and owned.get(str(target)) != existing:
                raise FileExistsError('Existing user-edited workflow is preserved: ' + str(target))
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        receipt.append({'id': job['id'], 'source': job['ui'], 'installed': str(target), 'sha256': digest})
    current = {r['installed'] for r in receipt}
    current_sources = {r['source'] for r in receipt}
    for old in previous.get('installed', []):
        source = ROOT / old['source']
        if old['source'] not in current_sources and source.is_relative_to(library / 'ui') and source.is_file():
            if hashlib.sha256(source.read_bytes()).hexdigest() == old['sha256']:
                source.unlink()
    for old_path, old_hash in owned.items():
        target = Path(old_path)
        if old_path not in current and target.is_relative_to(destination) and target.is_file():
            if hashlib.sha256(target.read_bytes()).hexdigest() == old_hash:
                target.unlink()
                parent = target.parent
                while parent != destination:
                    try: parent.rmdir()
                    except OSError: break
                    parent = parent.parent
    receipt_path.write_text(json.dumps({'installed': receipt, 'count': len(receipt)}, ensure_ascii=False, indent=2) + '\n')
    api_by_name = {Path(j['api']).name: (ROOT / j['api']) for j in catalog['workflows']}
    expected_api = set(api_by_name.values())
    for old in (library / 'api').rglob('*.api.json'):
        replacement = api_by_name.get(old.name)
        if old not in expected_api and replacement and old.read_bytes() == replacement.read_bytes():
            old.unlink()
    paths = {'catalog.json', 'README.md'}
    for job in catalog['workflows']:
        paths.add(str((ROOT / job['api']).relative_to(library)))
        if job.get('frontend_import', {}).get('pass'):
            paths.add(str((ROOT / job['ui']).relative_to(library)))
    paths.update('input/' + p for p in catalog['input_assets'])
    archive = library / 'model-feature-workflows.zip'
    temporary = archive.with_suffix('.zip.tmp')
    with ZipFile(temporary, 'w', ZIP_DEFLATED, compresslevel=1) as bundle:
        for path in sorted(paths):
            bundle.write(library / path, 'model-feature-workflows/' + path)
    with ZipFile(temporary) as bundle:
        assert bundle.testzip() is None
    temporary.replace(archive)
    lightweight = library / 'model-feature-workflows-light.zip'
    caches = {'input/' + p for p,a in catalog['input_assets'].items() if a.get('kind') == 'conditioning_not_model_weights'}
    temporary = lightweight.with_suffix('.zip.tmp')
    with ZipFile(temporary, 'w', ZIP_DEFLATED, compresslevel=1) as bundle:
        for path in sorted(paths - caches): bundle.write(library / path, 'model-feature-workflows/' + path)
    with ZipFile(temporary) as bundle:
        assert bundle.testzip() is None
    temporary.replace(lightweight)
    write_bundle_status(catalog_bytes, len(receipt))
    print(json.dumps({'installed_ui': len(receipt), 'bundle_files': len(paths), 'zip_bytes': archive.stat().st_size,
                      'light_zip_bytes': lightweight.stat().st_size}))


if __name__ == '__main__':
    install()
