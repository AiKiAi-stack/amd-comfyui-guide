"""Keep preflight blocks separate from the new explicitly submitted cases."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
path = HERE / "blocked.json"
items = json.loads(path.read_text(encoding="utf-8"))
superseded = {"qwen-turbo-un-t2i-white-cat-512", "qwen-turbo-un-inpaint", "qwen-turbo-un-multiref"}
items = [item for item in items if item["id"] not in superseded]
for item in items:
    item.setdefault("reason", item.get("review", {}).get("detail", ""))
path.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
