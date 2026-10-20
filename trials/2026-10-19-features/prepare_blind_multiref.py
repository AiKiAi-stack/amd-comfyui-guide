import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
path = HERE / "cases.json"
cases = json.loads(path.read_text(encoding="utf-8"))
for case in cases:
    if case["id"] not in {"qwen-multiref", "turbo-un-multiref"}:
        continue
    if (HERE / "cases" / case["id"] / "result.json").exists():
        raise RuntimeError("Do not change a submitted case's prompt")
    case["prompt"] = "Use image 1 as the background and composition. Remove the existing animal in image 1 and place the animal subject from image 2 at the same location. Take its species, shape, fur colors and identifying features from image 2. Preserve the background, lighting, framing and perspective of image 1. Do not copy the background of image 2. Photorealistic."
    case["claim_level"] += "；提示词不点名第二图主体，减少仅靠文字猜中任务的可能"
path.write_text(json.dumps(cases, ensure_ascii=False, indent=2), encoding="utf-8")
