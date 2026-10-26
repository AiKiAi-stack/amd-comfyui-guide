"""Run one distinct real-model case; save the response and measurable evidence."""
import argparse
import json
from pathlib import Path
import time
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument("case", choices=["preset", "clone", "long", "design", "freeform"])
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=True)
base = "http://127.0.0.1:7861"
started = time.perf_counter()

if args.case == "preset":
    text = "你好，欢迎使用本地语音工作台。"
    query = urllib.parse.urlencode({"text": text, "speaker": "灵小柔", "seed": 1895})
    with urllib.request.urlopen(base + "/api?" + query, timeout=600) as response:
        data = response.read()
        assert response.headers.get_content_type() == "audio/wav"
        assert data[:4] == b"RIFF" and len(data) > 10000
        path = args.output / "preset.wav"
        path.write_bytes(data)
        result = {"text": text, "file": str(path), "response_headers": dict(response.headers)}
else:
    from gradio_client import Client, handle_file
    client = Client(base, download_files=str(args.output / "downloads"), verbose=False)
    request = {"text": "夜色渐渐深了，愿你今晚睡个好觉。", "mode": "内置音色", "speaker": "灵小柔",
               "reference_audio": None, "reference_text": "", "instruction": "", "language": "中文",
               "seed": 1895, "segment_length": 24}
    if args.case == "clone":
        request.update(mode="声音克隆", reference_audio=handle_file(str(ROOT / "upstream/data/voice_presets/voice_audio/lingguang.wav")),
                       reference_text="诶，你今天有空吗？我们能不能聊聊这件事啊？")
    elif args.case == "long":
        request["text"] = (ROOT / "research/long-text.txt").read_text()
        # Longer clauses reduce the number of joins while still testing many segments.
        request["segment_length"] = 64
    elif args.case == "design":
        request.update(mode="音色设计", instruction="温暖、沉稳的青年男声，像在讲睡前故事。")
    elif args.case == "freeform":
        request.update(mode="表演指令", instruction="轻声而温柔地说话，语气平静自然。")
    prediction = client.predict(**request, api_name="/synthesize")
    metrics = prediction[3]
    assert metrics["audio_seconds"] > 0.5 and metrics["audio_rms"] > 1e-6
    if args.case == "long":
        assert metrics["characters"] > 800 and metrics["segment_count"] > 5
    result = {"request": {**request, "reference_audio": "official lingguang.wav" if args.case == "clone" else None},
              "audio": prediction[0], "status": prediction[1], "metrics": metrics}

result.update(case=args.case, wall_seconds=time.perf_counter() - started)
(args.output / (args.case + ".json")).write_text(json.dumps(result, ensure_ascii=False, indent=2))
print(json.dumps(result, ensure_ascii=False, indent=2))
