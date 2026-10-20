"""Export selected local trial evidence into this separate publication checkout.

Run once with --source <local experiment root>. Never copies environments/weights.
Re-run only in a disposable publication checkout: existing selected files are replaced.
"""
import argparse
import hashlib
import html
import json
import re
import struct
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
TEXT = {'.md', '.json', '.py', '.ps1', '.txt'}
MEDIA = {'.png', '.webp', '.jpg', '.jpeg'}


def links(text, suffix):
    if suffix == '.html':
        return re.findall(r'(?:href|src)=["\']([^"\']+)', text)
    if suffix == '.md':
        return re.findall(r'\]\(([^)]+)\)', text)
    return []


def strip_metadata(data, suffix):
    if suffix == '.png':
        output, index = data[:8], 8
        while index < len(data):
            length = struct.unpack('>I', data[index:index+4])[0]
            kind = data[index+4:index+8]
            block = data[index:index+length+12]
            if kind not in (b'tEXt', b'iTXt', b'zTXt', b'eXIf'):
                output += block
            index += length + 12
        return output
    if suffix == '.webp':
        blocks, index = [], 12
        while index + 8 <= len(data):
            kind = data[index:index+4]
            size = int.from_bytes(data[index+4:index+8], 'little')
            block = data[index:index+8+size+(size % 2)]
            if kind not in (b'EXIF', b'XMP '):
                if kind == b'VP8X':
                    block = block[:8] + bytes([block[8] & ~0x0c]) + block[9:]
                blocks.append(block)
            index += 8 + size + size % 2
        body = b'WEBP' + b''.join(blocks)
        return b'RIFF' + len(body).to_bytes(4, 'little') + body
    # JPEGs are excluded from this initial export rather than risking EXIF leaks.
    raise ValueError('Unsupported public image type: ' + suffix)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    args = parser.parse_args()
    source = args.source.resolve()
    if source == ROOT or source in ROOT.parents:
        parser.error('Source and publication checkout must be separate.')
    selected = set()
    excluded = {'source-file-index.json', 'source-metrics.json', 'hf-search.json', 'source-judge-summary.json'}
    for folder in ('trials', 'research'):
        for file in (source / folder).rglob('*'):
            if not file.is_file() or '__pycache__' in file.parts or 'service-logs' in file.parts:
                continue
            if file.suffix.lower() in TEXT and file.name not in excluded and file.stat().st_size < 2_000_000:
                selected.add(file)
    report = source / 'trials/2026-10-19-features/feature-report.html'
    selected.add(report)
    for file in source.glob('*.json'):
        selected.add(file)
    for folder in ('gfx1032_quant_fallback', 'feature_bench_ordering'):
        file = source / 'ComfyUI/custom_nodes' / folder / '__init__.py'
        dest = ROOT / 'code_source' / folder / '__init__.py'
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(file.read_bytes())
    # Only H3 helper source, never its clone, venv, model files or cached downloads.
    for file in (source / 'h3-sandbox').glob('*'):
        if file.is_file() and file.suffix.lower() in TEXT:
            selected.add(file)

    # Follow report/document links and JSON media paths within the source tree.
    queue = list(selected)
    visited = set()
    while queue:
        file = queue.pop()
        if file in visited:
            continue
        visited.add(file)
        if file.suffix.lower() not in TEXT | {'.html'}:
            continue
        content = file.read_text(encoding='utf-8-sig', errors='replace')
        candidates = []
        for ref in links(content, file.suffix.lower()):
            ref = html.unescape(unquote(ref)).split('#')[0].split('?')[0]
            if not ref or urlsplit(ref).scheme or ref.startswith('//'):
                continue
            candidates.append((file.parent / ref).resolve())
        if file.suffix == '.json':
            try:
                values = []
                def walk(obj):
                    if isinstance(obj, str): values.append(obj)
                    elif isinstance(obj, list):
                        for value in obj: walk(value)
                    elif isinstance(obj, dict):
                        for value in obj.values(): walk(value)
                walk(json.loads(content))
                for value in values:
                    p = Path(value)
                    if p.is_absolute() and p.suffix.lower() in MEDIA:
                        candidates.append(p.resolve())
            except (ValueError, OSError):
                pass
        for p in candidates:
            allowed = p.is_relative_to(source)
            if allowed and p.is_relative_to(source / 'ComfyUI'):
                allowed = any(p.is_relative_to(source / 'ComfyUI' / folder) for folder in ('input', 'output'))
            if allowed and p.is_file() and p.suffix.lower() in TEXT | {'.html', '.png', '.webp'}:
                if p not in selected:
                    selected.add(p)
                    queue.append(p)

    def sanitize(text):
        for prefix in (str(source), str(source).replace('\\', '/')):
            for form in (prefix, prefix.replace('\\', '\\\\')):
                replacement = 'D:/AI/comfyui-rx6650xt-lab'
                text = text.replace(form, replacement)
        # No private article snapshots, OS profile names, network shares or auth links.
        text = re.sub(r'[A-Z]:[\\/]+Users[\\/]+[^\\/\s"<>]+', 'D:/PUBLIC_USER', text, flags=re.I)
        text = re.sub(r'D:(?:\\\\|\\|/)+Downloads(?:\\\\|\\|/)+WeChatArticles[^\n"\'<>`]*', '[private-article-snapshot]', text, flags=re.I)
        text = re.sub(r'https?://(?:pan\.quark\.cn|pan\.baidu\.com|drive\.google\.com)/[^\s"<>)]*', 'https://example.invalid/private-share-removed', text)
        text = re.sub(r'https?://[^\s"<>)]*(?:X-Amz-Signature|X-Xet-Cas-Uid|Signature=)[^\s"<>)]*', 'https://example.invalid/signed-url-removed', text, flags=re.I)
        text = re.sub(r'(?<![\d.])(?:192\.168\.[0-9]{1,3}\.[0-9]{1,3}|10\.0\.[0-9]{1,3}\.[0-9]{1,3})(?![\d.])', '127.0.0.1', text)
        return text

    media = []
    for file in sorted(selected):
        relative = file.relative_to(source)
        dest = ROOT / relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        suffix = file.suffix.lower()
        if suffix in MEDIA:
            original = file.read_bytes()
            public = strip_metadata(original, suffix)
            dest.write_bytes(public)
            media.append({'file': relative.as_posix(), 'original_sha256': hashlib.sha256(original).hexdigest(),
                          'public_sha256': hashlib.sha256(public).hexdigest(), 'change': 'metadata removed, visual bitstream unchanged'})
        else:
            content = file.read_text(encoding='utf-8-sig', errors='replace')
            if suffix == '.json':
                # Sanitize decoded strings then encode, preserving JSON escaping.
                def clean(value):
                    if isinstance(value, str): return sanitize(value)
                    if isinstance(value, list): return [clean(v) for v in value]
                    if isinstance(value, dict): return {k: clean(v) for k, v in value.items()}
                    return value
                content = json.dumps(clean(json.loads(content)), ensure_ascii=False, indent=2)
            else:
                content = sanitize(content)
            dest.write_text(content, encoding='utf-8')
    (ROOT / 'environment').mkdir(exist_ok=True)
    (ROOT / 'environment/media-provenance.json').write_text(json.dumps(media, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'selected_files': len(selected), 'media': len(media), 'bytes': sum((ROOT / p.relative_to(source)).stat().st_size for p in selected)}, indent=2))


if __name__ == '__main__':
    main()
