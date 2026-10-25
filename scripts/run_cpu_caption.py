"""Run a verified local alternate VLM strictly on CPU; never download implicitly."""
import argparse
import hashlib
import json
from pathlib import Path
import time


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model-dir', type=Path, required=True)
    parser.add_argument('--image', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--threads', type=int, default=6)
    parser.add_argument('--max-new-tokens', type=int, default=64)
    args = parser.parse_args()
    if not 1 <= args.threads <= 32 or not 1 <= args.max_new_tokens <= 256:
        parser.error('Use 1..32 threads and 1..256 new tokens')
    manifest = json.loads((args.model_dir / 'verification.json').read_text())
    for item in manifest['files']:
        path = (args.model_dir / item['file']).resolve()
        if not path.is_relative_to(args.model_dir.resolve()) or sha(path) != item['sha256']:
            raise ValueError('Local model/config checksum changed: ' + item['file'])
    args.out.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    import torch
    from PIL import Image
    import psutil
    from transformers import AutoModelForImageTextToText, AutoProcessor

    torch.set_num_threads(args.threads)
    torch.set_num_interop_threads(1)
    processor = AutoProcessor.from_pretrained(args.model_dir, local_files_only=True, trust_remote_code=False)
    model = AutoModelForImageTextToText.from_pretrained(args.model_dir, local_files_only=True,
        trust_remote_code=False, dtype=torch.float32, attn_implementation='eager').to('cpu').eval()
    if any(parameter.device.type != 'cpu' for parameter in model.parameters()):
        raise RuntimeError('CPU-only caption invariant violated')
    instruction = 'Describe this image in one short sentence. Mention the animal, the setting and the lighting.'
    messages = [{'role': 'user', 'content': [{'type': 'image'}, {'type': 'text', 'text': instruction}]}]
    prompt = processor.apply_chat_template(messages, add_generation_prompt=True)
    image = Image.open(args.image).convert('RGB')
    inputs = processor(text=prompt, images=[image], return_tensors='pt').to('cpu')
    generation_start = time.monotonic()
    with torch.inference_mode():
        output = model.generate(**inputs, do_sample=False, max_new_tokens=args.max_new_tokens)
    new_ids = output[:, inputs['input_ids'].shape[-1]:]
    caption = processor.batch_decode(new_ids, skip_special_tokens=True)[0].strip()
    if not caption:
        raise ValueError('Model returned an empty caption')
    (args.out / 'caption.txt').write_text(caption, encoding='utf-8')
    record = {'status': 'caption_generated_visual_review_required', 'caption': caption,
        'model': manifest['repo'], 'revision': manifest['revision'],
        'model_manifest_sha256': sha(args.model_dir / 'verification.json'),
        'input_sha256': sha(args.image), 'instruction': instruction,
        'caption_sha256': sha(args.out / 'caption.txt'), 'device': 'cpu', 'dtype': 'float32',
        'threads': args.threads, 'new_tokens': int(new_ids.shape[-1]),
        'generation_seconds': time.monotonic() - generation_start,
        'load_and_generation_seconds': time.monotonic() - started,
        'rss_after_bytes': psutil.Process().memory_info().rss,
        'scope': 'Explicit alternate caption model; original Qwen8B CPU configuration remains separate'}
    (args.out / 'result.json').write_text(json.dumps(record, indent=2), encoding='utf-8')
    print(json.dumps(record, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
