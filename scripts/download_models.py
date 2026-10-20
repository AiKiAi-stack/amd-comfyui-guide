"""Download only a selected pinned HF manifest, verifying bytes and SHA-256."""
import argparse
import hashlib
import json
from pathlib import Path
from urllib.parse import quote
from urllib.request import urlopen


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest', type=Path)
    parser.add_argument('--comfy', type=Path, required=True)
    args = parser.parse_args()
    records = json.loads(args.manifest.read_text(encoding='utf-8-sig'))
    if not isinstance(records, list):
        parser.error('Expected a list manifest with repo/revision/file/bytes/sha256/target.')
    for row in records:
        target = str(row['target']).replace('\\', '/')
        if '/models/' not in target:
            raise ValueError('Missing models directory in target')
        relative = Path(target.split('/models/', 1)[1])
        model_root = (args.comfy / 'models').resolve()
        dest = (model_root / relative).resolve()
        if not dest.is_relative_to(model_root):
            raise ValueError('Unsafe destination')
        expected = row['sha256'].lower()

        def valid(path):
            if not path.exists() or path.stat().st_size != row['bytes']:
                return False
            with path.open('rb') as stream:
                return hashlib.file_digest(stream, 'sha256').hexdigest() == expected

        if valid(dest):
            print('VERIFIED existing', relative)
            continue
        if dest.exists():
            raise SystemExit(f'Refusing to replace an unverified existing file: {dest}')
        dest.parent.mkdir(parents=True, exist_ok=True)
        part = dest.with_name(dest.name + '.part')
        url = 'https://huggingface.co/' + row['repo'] + '/resolve/' + quote(row['revision'], safe='') + '/' + quote(row['file'], safe='/')
        print('DOWNLOAD', relative, row['bytes'], flush=True)
        with urlopen(url, timeout=120) as source, part.open('wb') as out:
            while block := source.read(4 * 1024 * 1024):
                out.write(block)
        if not valid(part):
            raise SystemExit(f'Checksum/size mismatch; retained {part}')
        part.rename(dest)
        print('VERIFIED', relative)


if __name__ == '__main__':
    main()
