"""Recover only PNGs whose embedded graph matches a crashed submitted batch."""
import json
from pathlib import Path
import sys
from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
folder = HERE / "batches" / sys.argv[1]
api = json.loads((folder / "batch-api.json").read_text(encoding="utf-8"))
manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))

def values(graph):
    return {key: {"class_type": value.get("class_type"), "inputs": value.get("inputs")} for key, value in graph.items()}

for item in manifest:
    found = []
    for output in item["output_nodes"]:
        prefix = ROOT / "ComfyUI/output" / output["filename_prefix"]
        for path in prefix.parent.glob(prefix.name + "_*.png"):
            with Image.open(path) as image:
                recorded = json.loads(image.info.get("prompt", "null"))
            if not isinstance(recorded, dict) or values(recorded) != values(api):
                continue
            found.append({"path": str(path), "filename": path.name, "role": output["role"], "node_id": output["node_id"]})
    if not any(image["role"] == "main" for image in found):
        continue
    result_path = HERE / "cases" / item["id"] / "result.json"
    result = json.loads(result_path.read_text(encoding="utf-8"))
    backup = result_path.with_name("result-before-output-recovery.json")
    if backup.exists():
        raise RuntimeError("Recovery already performed")
    backup.write_bytes(result_path.read_bytes())
    result.update(status="partial_output", images=found,
                  recovery="Output PNG exists and its embedded node classes/inputs match this batch. The whole batch aborted and no successful API history is claimed.")
    result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print("RECOVERED", item["id"], len(found), "files; batch remains failed")
