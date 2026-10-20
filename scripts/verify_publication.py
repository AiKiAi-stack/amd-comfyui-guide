"""Check the public snapshot without loading ComfyUI or a GPU."""
import ast
import hashlib
import json
import re
import struct
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit
from html import unescape

ROOT = Path(__file__).resolve().parents[1]
IGNORED = {'.git', '.venv', 'runtime', 'runs', '__pycache__'}


def files():
    return sorted(p for p in ROOT.rglob('*') if p.is_file() and not IGNORED.intersection(p.relative_to(ROOT).parts))


def main():
    errors, broken, warnings = [], [], []
    all_files = files()
    for p in all_files:
        rel = p.relative_to(ROOT).as_posix()
        if p.stat().st_size > 20_000_000:
            errors.append(rel + ': unexpectedly large file')
        if p.suffix in {'.gguf', '.safetensors', '.whl', '.log', '.pid', '.env'}:
            errors.append(rel + ': excluded file type')
        if p.suffix in {'.md', '.html', '.json', '.py', '.ps1', '.txt', '.yml'}:
            s = p.read_text(encoding='utf-8-sig')
            patterns = [r'gh[pousr]_[A-Za-z0-9]{20,}', r'github_pat_[A-Za-z0-9_]{20,}',
                        r'hf_[A-Za-z0-9]{20,}', r'sk-[A-Za-z0-9_-]{24,}',
                        r'-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----',
                        r'[A-Z]:[\\/]+Users[\\/]+[^\\/\s"<>]+',
                        r'https?://[^\s"<>]*[?&](?:token|access_token|signature|x-amz-signature)=']
            for pattern in patterns:
                if re.search(pattern, s, flags=re.I):
                    errors.append(rel + ': possible credential/personal path (value withheld)')
                    break
            if p.suffix == '.json':
                try: json.loads(s)
                except ValueError as e: errors.append(rel + ': invalid JSON ' + str(e))
            if p.suffix == '.py':
                try: ast.parse(s)
                except SyntaxError as e: errors.append(rel + ': invalid Python ' + str(e))
            if p.suffix == '.html':
                refs = re.findall(r'(?:href|src)=["\']([^"\']+)', s)
            elif p.suffix == '.md':
                # Ignore inline code: examples there are not document links.
                refs = re.findall(r'\]\(([^)]+)\)', re.sub(r'`[^`\n]*`', '', s))
            else:
                refs = []
            for ref in refs:
                ref = unescape(unquote(ref)).split('#')[0].split('?')[0].strip('<>')
                if not ref or urlsplit(ref).scheme or ref.startswith('//'):
                    continue
                target = (p.parent / ref).resolve()
                if not target.is_relative_to(ROOT) or not target.exists():
                    broken.append({'file': rel, 'target': ref})
        if p.suffix == '.png':
            data, index = p.read_bytes(), 8
            while index + 12 <= len(data):
                size = struct.unpack('>I', data[index:index+4])[0]
                if data[index+4:index+8] in (b'tEXt', b'iTXt', b'zTXt', b'eXIf'):
                    errors.append(rel + ': PNG metadata')
                index += size + 12
        if p.suffix == '.webp':
            data, index = p.read_bytes(), 12
            while index + 8 <= len(data):
                size = int.from_bytes(data[index+4:index+8], 'little')
                if data[index:index+4] in (b'EXIF', b'XMP '):
                    errors.append(rel + ': WebP metadata')
                index += size + 8 + size % 2
    manifest_path = ROOT / 'publication-manifest.json'
    if '--write-manifest' in sys.argv:
        manifest = {'date': '2026-10-20', 'scope': 'Public sanitized tutorial snapshot; historical image hashes refer to local originals.',
                    'files': {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                              for p in all_files if p != manifest_path}}
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    elif manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
        for name, expected in manifest['files'].items():
            p = ROOT / name
            if not p.exists() or hashlib.sha256(p.read_bytes()).hexdigest() != expected:
                errors.append(name + ': manifest mismatch')
    print(json.dumps({'files': len(all_files), 'errors': errors, 'broken_links': broken,
                      'warnings': warnings}, ensure_ascii=False, indent=2))
    if errors or broken:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
