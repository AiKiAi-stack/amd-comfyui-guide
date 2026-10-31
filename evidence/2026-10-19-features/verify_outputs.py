"""Audit image-to-feature bindings and masked-composite preservation."""
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
from urllib.parse import unquote

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
cases = json.loads((HERE / "cases.json").read_text(encoding="utf-8"))
records = []

def graph_values(graph):
    if not isinstance(graph, dict):
        return graph
    # ComfyUI adds LoadImage is_changed cache hashes at execution time.
    # Compare the actual node classes and inputs; keep hashes as provenance.
    return {key: {"class_type": value.get("class_type"), "inputs": value.get("inputs")} for key, value in graph.items()}

for case in cases:
    folder = HERE / "cases" / case["id"]
    result_file = folder / "result.json"
    if not result_file.exists():
        continue
    result = json.loads(result_file.read_text(encoding="utf-8"))
    record = {"id": case["id"], "feature": case["feature"], "status": result.get("status"), "prompt_id": result.get("prompt_id"), "images": []}
    graph_file = folder / "api.json"
    api = json.loads(graph_file.read_text(encoding="utf-8")) if graph_file.exists() else None
    for image_record in result.get("images", []):
        filename = image_record.get("path") if isinstance(image_record, dict) else image_record
        path = Path(filename)
        entry = {"path": str(path), "exists": path.is_file()}
        if path.is_file():
            with Image.open(path) as img:
                image_prompt = json.loads(img.info.get("prompt", "null"))
                entry.update(width=img.width, height=img.height,
                             png_prompt_matches_api=graph_values(image_prompt) == graph_values(api),
                             belongs_to_case=path.name.startswith(case["id"] + "_") or path.name.startswith(case["id"] + "-"))
                if isinstance(image_prompt, dict):
                    entry["input_cache_hashes"] = {key: value["is_changed"] for key, value in image_prompt.items() if "is_changed" in value}
            entry["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        record["images"].append(entry)
    if case.get("recipe") == "inpaint" or case.get("mask_attachments"):
        paths = [Path(p["path"] if isinstance(p, dict) else p) for p in result.get("images", [])]
        main = next((p for p in paths if p.name.startswith(case["id"] + "_")), None)
        mask = next((p for p in paths if p.name.startswith(case["id"] + "-mask_")), None)
        source = next((p for p in paths if p.name.startswith(case["id"] + "-input_")), None)
        if all(p and p.is_file() for p in (main, mask, source)):
            out = np.asarray(Image.open(main).convert("RGB"), dtype=np.int16)
            original = np.asarray(Image.open(source).convert("RGB"), dtype=np.int16)
            mask_values = np.asarray(Image.open(mask).convert("L"))
            diff = np.abs(out - original)
            outside = mask_values == 0
            inside = mask_values > 0
            record["mask_measurement"] = {
                "outside_pixels": int(outside.sum()),
                "outside_changed_pixels": int((diff[outside].max(axis=1) > 0).sum()),
                "outside_max_channel_difference_0_to_255": int(diff[outside].max()),
                "inside_pixels": int(inside.sum()),
                "inside_changed_pixels": int((diff[inside].max(axis=1) > 0).sum()),
                "meaning": "Mask-outside preservation is provided by the final compositing node, not attributed solely to the model.",
            }
    records.append(record)

class AssetParser(HTMLParser):
    assets = []
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "img" and attrs.get("src"):
            self.assets.append(attrs["src"])

parser = AssetParser()
report = HERE.parents[1] / "report/index.html"
if report.exists():
    parser.feed(report.read_text(encoding="utf-8"))
missing = [src for src in parser.assets if not (report.parent / unquote(src)).resolve().is_file()]
audit = {"records": records, "report_image_count": len(parser.assets), "missing_report_images": missing}
(HERE / "output-audit.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
bad = [image for record in records for image in record["images"] if not image.get("exists") or not image.get("belongs_to_case") or not image.get("png_prompt_matches_api")]
print(json.dumps({"cases_with_results": len(records), "images_with_binding_or_metadata_errors": len(bad), "missing_report_images": len(missing)}, ensure_ascii=False))
if bad or missing:
    raise SystemExit(1)
