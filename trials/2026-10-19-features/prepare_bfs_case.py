import copy
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
path = HERE / "cases.json"
cases = json.loads(path.read_text(encoding="utf-8"))
if not any(case["id"] == "qwen-bfs-head-swap" for case in cases):
    case = copy.deepcopy(next(case for case in cases if case["id"] == "qwen-face-swap"))
    case.update(id="qwen-bfs-head-swap", feature="换头／BFS 专用 LoRA 对照", claim_level="第三方 BFS 专用方案的本机探索；15步且未使用Pruna8步LoRA，不是作者整合包复现")
    case["prompt"] = "head_swap: " + case["prompt"]
    case["lora"] = {"name": "bfs_head_v1.1_qwen_2.1.safetensors", "strength": 1.0}
    case["expected"] = "在原双图任务上加 BFS LoRA，头部采用 A，同时保留 B 的红围巾、大衣、公园、头部角度；本机15步实验，不能称复现含Pruna的官方8步配方。"
    cases.append(case)
    path.write_text(json.dumps(cases, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Added", case["id"])
