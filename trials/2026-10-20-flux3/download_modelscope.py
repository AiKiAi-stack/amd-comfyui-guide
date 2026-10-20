"""Download pinned ModelScope components with resumable transfer and SHA-256 receipts."""
import argparse
import hashlib
import json
from pathlib import Path
import time

import requests

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
REPO = "junwenlu/flux-3-image-klein-ComfyUI"
BASE = f"https://www.modelscope.cn/api/v1/models/{REPO}/repo"


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def prepare():
    HERE.mkdir(parents=True, exist_ok=True)
    response = requests.get(BASE + "/files", params={"Revision": "master", "Recursive": "true"}, timeout=45)
    response.raise_for_status()
    metadata = response.json()
    if not metadata.get("Success"):
        raise RuntimeError("ModelScope metadata request failed")
    write_json(HERE / "modelscope-source-metadata.json", metadata)
    revision = metadata["Data"]["LatestCommitter"]["Id"] or next(f["Revision"] for f in metadata["Data"]["Files"] if f["Path"] == "README.md")
    manifest = []
    for item in metadata["Data"]["Files"]:
        name = item["Path"]
        if item["Type"] != "blob" or not (name.endswith(".safetensors") or name.startswith("workflows/") or name == "README.md"):
            continue
        target = ROOT / "ComfyUI/models" / name if name.endswith(".safetensors") else HERE / "source_workflows" / Path(name).name
        manifest.append({"repo": REPO, "revision": revision, "file": name, "bytes": item["Size"], "sha256": item["Sha256"], "target": str(target), "source": BASE})
    write_json(HERE / "modelscope-download-manifest.json", manifest)
    return manifest


def download(item):
    target = Path(item["target"])
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_name(target.name + ".part")
    receipt = HERE / (target.name + ".verified.json")
    if target.exists() and receipt.exists():
        prior = json.loads(receipt.read_text(encoding="utf-8"))
        if target.stat().st_size == item["bytes"] and prior.get("verified_sha256") == item["sha256"]:
            print("ALREADY VERIFIED", target.name, flush=True)
            return
    candidate = target if target.exists() else partial
    if not target.exists():
        for attempt in range(5):
            offset = partial.stat().st_size if partial.exists() else 0
            if offset == item["bytes"]:
                break
            if offset > item["bytes"]:
                raise RuntimeError("Partial file exceeds expected size; preserve and inspect it")
            try:
                with requests.get(item["source"], params={"Revision": item["revision"], "FilePath": item["file"]}, headers={"Range": f"bytes={offset}-"} if offset else {}, stream=True, timeout=(30, 120)) as response:
                    response.raise_for_status()
                    if offset and response.status_code != 206:
                        raise RuntimeError("Server did not honor resume; partial retained")
                    print("DOWNLOAD", target.name, offset, "/", item["bytes"], flush=True)
                    last = time.monotonic()
                    with partial.open("ab" if offset else "wb") as out:
                        for chunk in response.iter_content(8 * 1024 * 1024):
                            out.write(chunk)
                            offset += len(chunk)
                            if time.monotonic() - last > 30:
                                print("PROGRESS", target.name, offset, "/", item["bytes"], flush=True)
                                last = time.monotonic()
                break
            except requests.RequestException:
                if attempt == 4:
                    raise
                time.sleep(3)
    if candidate.stat().st_size != item["bytes"]:
        raise RuntimeError(f"Byte mismatch: {target.name}")
    print("VERIFY", target.name, flush=True)
    with candidate.open("rb") as source:
        actual = hashlib.file_digest(source, "sha256").hexdigest()
    if actual != item["sha256"]:
        raise RuntimeError(f"SHA-256 mismatch: {target.name}")
    if candidate == partial:
        partial.replace(target)
    write_json(receipt, {**item, "verified_sha256": actual, "completed_at": time.strftime("%Y-%m-%dT%H:%M:%S%z")})
    print("VERIFIED", target.name, actual, flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--small-only", action="store_true")
    parser.add_argument("--weights-only", action="store_true")
    args = parser.parse_args()
    manifest_path = HERE / "modelscope-download-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else prepare()
    # Small workflow files are available before the multi-GB weights.
    for item in sorted(manifest, key=lambda item: item["bytes"]):
        is_weight = item["file"].endswith(".safetensors")
        if (args.small_only and is_weight) or (args.weights_only and not is_weight):
            continue
        download(item)
