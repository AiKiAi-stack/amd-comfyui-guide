import copy
import json
import shutil
import sys
import time
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parents[2]
TRIAL = Path(__file__).resolve().parent
COMFY = ROOT / "ComfyUI"
BASE = "http://127.0.0.1:8188"


def main():
    resolution = int(sys.argv[1]) if len(sys.argv) > 1 else 768
    label = f"qwen-base-edit-{resolution}" if resolution != 768 else "qwen-base-edit"
    source = COMFY / "output" / "QwenImage21_RX6650XT_768_00001_.png"
    target = COMFY / "input" / "liuyue-qwen-base-source.png"
    shutil.copy2(source, target)

    graph = json.loads((ROOT / "qwen-image-2.1-768-api.json").read_text(encoding="utf-8"))
    graph = copy.deepcopy(graph)
    graph["8"] = {"class_type": "LoadImage", "inputs": {"image": target.name}}
    graph["4"]["inputs"]["images.image_1"] = ["8", 0]
    graph["4"]["inputs"]["prompt"] = (
        "Edit the reference image: turn the orange cat into a fluffy white cat. "
        "Keep the cat's pose, the rainy Shanghai street, cafe window, neon reflections, "
        "camera framing and lighting the same. Photorealistic. No text."
    )
    graph["4"]["inputs"]["negative_prompt"] = "orange fur, extra animals, blur, text, watermark"
    graph["7"]["inputs"]["filename_prefix"] = "Liuyue_Qwen21_Base_Edit_RX6650XT"
    graph["5"]["inputs"]["seed"] = 2106651
    graph["4"]["inputs"]["resolution"] = resolution
    if resolution < 768:
        graph["5"]["inputs"]["steps"] = 15
    (TRIAL / f"{label}-api.json").write_text(
        json.dumps(graph, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    response = requests.post(BASE + "/prompt", json={"prompt": graph}, timeout=30)
    response.raise_for_status()
    submission = response.json()
    (TRIAL / f"{label}-submission.json").write_text(
        json.dumps(submission, indent=2), encoding="utf-8"
    )
    if submission.get("error") or not submission.get("prompt_id"):
        raise RuntimeError(submission)
    print("SUBMITTED", submission["prompt_id"], flush=True)

    deadline = time.monotonic() + 1800
    while time.monotonic() < deadline:
        response = requests.get(BASE + "/history/" + submission["prompt_id"], timeout=30)
        response.raise_for_status()
        history = response.json().get(submission["prompt_id"])
        if history:
            (TRIAL / f"{label}-history.json").write_text(
                json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            print("DONE", json.dumps(history.get("status")), flush=True)
            print("OUTPUTS", json.dumps(history.get("outputs")), flush=True)
            if history.get("status", {}).get("status_str") != "success":
                sys.exit(1)
            return
        time.sleep(10)
    raise TimeoutError("ComfyUI prompt did not complete within 30 minutes")


if __name__ == "__main__":
    main()
