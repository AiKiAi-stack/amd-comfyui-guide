import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
path = HERE / "cases.json"
cases = json.loads(path.read_text(encoding="utf-8"))
for case in cases:
    if case["model"] != "turbo-un":
        continue
    if (HERE / "cases" / case["id"] / "result.json").exists():
        raise RuntimeError("Do not change the runtime profile of an existing result")
    case["runtime_profile"] = "本轮用 --disable-dynamic-vram --lowvram 将 UN GGUF 文字／视觉编码器留在 CPU，扩散采样在 RX 6650 XT，VAE 在 CPU；8步。用于规避前轮 GGUF 编码器卸载崩溃，不是纯 GPU 流程，未测试去限制效果。"
path.write_text(json.dumps(cases, ensure_ascii=False, indent=2), encoding="utf-8")
