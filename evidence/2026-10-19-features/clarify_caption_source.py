import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
path = HERE / "cases.json"
cases = json.loads(path.read_text(encoding="utf-8"))
for case in cases:
    if case["id"] == "qwen-caption":
        case["claim_level"] = "同作者较早 Qwen 站外记录提到自动提示词，非当前公众号原文确认；本轮以核心 TextGenerate 作额外工作流测试"
path.write_text(json.dumps(cases, ensure_ascii=False, indent=2), encoding="utf-8")
