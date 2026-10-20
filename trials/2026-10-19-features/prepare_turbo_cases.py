"""Add exact Turbo-UN combination tests without changing the finished base cases."""
import copy
import json
from pathlib import Path

here = Path(__file__).resolve().parent
path = here / "cases.json"
cases = json.loads(path.read_text(encoding="utf-8"))
ids = {case["id"] for case in cases}
new = [{
    "id": "turbo-un-t2i", "model": "turbo-un", "feature": "原生 8 步文生图",
    "recipe": "t2i", "claim_level": "作者站外演示及上游；使用 UN 编码器组合独立重试",
    "inputs": [], "prompt": "A fluffy white cat in a rain-soaked Shanghai cafe, looking out at neon reflections. Cinematic photorealism, warm indoor light, no text.",
    "expected": "UN GGUF 编码器配合 Turbo Q4 主模型真实完成 8 步，生成白猫与雨夜咖啡馆。前轮普通 Turbo 的出图不能充当本项输出。",
}]
for original_id in ("qwen-inpaint", "qwen-multiref", "qwen-face-swap"):
    case = copy.deepcopy(next(case for case in cases if case["id"] == original_id))
    case["id"] = original_id.replace("qwen-", "turbo-un-")
    case["model"] = "turbo-un"
    case["claim_level"] = "公众号索引/作者站外演示；独立 UN 编码器组合"
    new.append(case)
cases.extend(case for case in new if case["id"] not in ids)
path.write_text(json.dumps(cases, ensure_ascii=False, indent=2), encoding="utf-8")
print("Added", [case["id"] for case in new if case["id"] not in ids])
