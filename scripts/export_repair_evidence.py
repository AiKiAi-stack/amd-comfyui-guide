"""Export one reviewed repair case with image bindings and pixel-identical public PNGs."""
import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", type=Path, required=True, help="Replay case directory")
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--review", type=Path, required=True)
    parser.add_argument("--original-workflow", type=Path)
    parser.add_argument("--encoding-case", type=Path)
    parser.add_argument("--sampling-case", type=Path,
                        help="Actual sampling case when --case is a separate CPU decode")
    parser.add_argument("--phase-link", type=Path)
    parser.add_argument("--caption", type=Path)
    args = parser.parse_args()
    target = args.destination
    target.mkdir(parents=True, exist_ok=False)
    review = json.loads(args.review.read_text(encoding="utf-8"))
    if review["verdict"] not in {"pass", "partial", "fail"} or not review.get("review"):
        parser.error("Provide an explicit visual verdict and review")
    result = json.loads((args.case / "result.json").read_text(encoding="utf-8"))
    history_path = args.case / "history.json"
    history = json.loads(history_path.read_text(encoding="utf-8"))
    prompt_id, entry = next(iter(history.items()))
    result.update(review)
    result["prompt_id"] = prompt_id
    result["raw_history_sha256"] = sha(history_path)
    result.pop("visual_verdict", None)
    result["images"] = []
    for image_record in json.loads((args.case / "result.json").read_text())["images"]:
        original = args.case / image_record["file"]
        if not original.resolve().is_relative_to(args.case.resolve()):
            raise ValueError("Output image must stay within its replay case")
        assert sha(original) == image_record["sha256"]
        published = target / original.name
        with Image.open(original) as image:
            clean = Image.frombytes(image.mode, image.size, image.tobytes())
            clean.save(published)
            with Image.open(published) as check:
                assert check.mode == image.mode and check.size == image.size and check.tobytes() == image.tobytes()
        result["images"].append({"file": published.name, "original_sha256": sha(original),
                                 "public_sha256": sha(published), "pixels_unchanged": True})
    (target / "sampling.api.json").write_bytes((args.case / "api.json").read_bytes())
    if args.sampling_case:
        (target / "decoding.api.json").write_bytes((args.case / "api.json").read_bytes())
        (target / "sampling.api.json").write_bytes((args.sampling_case / "api.json").read_bytes())
        result["decoding_elapsed_seconds"] = result["elapsed_seconds"]
        result["sampling_result"] = json.loads((args.sampling_case / "result.json").read_text())
        result["sampling_history_sha256"] = sha(args.sampling_case / "history.json")
    (target / "history-binding.json").write_text(json.dumps({"prompt_id": prompt_id,
        "status": entry["status"]["status_str"], "outputs": entry.get("outputs", {})}, indent=2), encoding="utf-8")
    if args.original_workflow:
        (target / "workflow.api.json").write_bytes(args.original_workflow.read_bytes())
        result["workflow_sha256"] = sha(args.original_workflow)
    if args.encoding_case:
        (target / "encoding.api.json").write_bytes((args.encoding_case / "api.json").read_bytes())
        result["encoding_result"] = json.loads((args.encoding_case / "result.json").read_text())
        result["encoding_history_sha256"] = sha(args.encoding_case / "history.json")
    if args.phase_link:
        (target / "phase-link.json").write_bytes(args.phase_link.read_bytes())
    if args.caption:
        (target / "caption.txt").write_bytes(args.caption.read_bytes())
        result["caption_sha256"] = sha(args.caption)
    (target / "result.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(target)


if __name__ == "__main__":
    main()
