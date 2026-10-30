import argparse
import hashlib
import json
import os
import time
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parent


def download(item):
    target = Path(item["target"])
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_name(target.name + ".part")
    receipt_path = ROOT / (target.name + ".verified.json")
    if target.is_file() and receipt_path.is_file():
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        if (target.stat().st_size == item["bytes"]
                and receipt.get("verified_sha256") == item["sha256"]
                and all(receipt.get(key) == item[key] for key in ("repo", "revision", "file", "target"))):
            print(f"ALREADY VERIFIED {target}", flush=True)
            return
    url = f"https://huggingface.co/{item['repo']}/resolve/{item['revision']}/{item['file']}"
    if not target.exists():
        for attempt in range(4):
            offset = partial.stat().st_size if partial.exists() else 0
            if offset == item["bytes"]:
                break
            headers = {"Range": f"bytes={offset}-"} if offset else {}
            print(f"DOWNLOAD {target.name}: {offset}/{item['bytes']} bytes", flush=True)
            try:
                with requests.get(url, headers=headers, stream=True, timeout=(30, 120)) as response:
                    response.raise_for_status()
                    if offset and response.status_code != 206:
                        raise RuntimeError("Server did not honor download resume")
                    mode = "ab" if offset else "wb"
                    last = time.monotonic()
                    with partial.open(mode) as out:
                        for chunk in response.iter_content(8 * 1024 * 1024):
                            out.write(chunk)
                            offset += len(chunk)
                            if time.monotonic() - last > 30:
                                print(f"PROGRESS {target.name}: {offset}/{item['bytes']} bytes", flush=True)
                                last = time.monotonic()
                break
            except requests.RequestException:
                if attempt == 3:
                    raise
                time.sleep(3)
        candidate = partial
    else:
        candidate = target
    if candidate.stat().st_size != item["bytes"]:
        raise RuntimeError(f"Size mismatch for {target.name}: {candidate.stat().st_size}")
    print(f"VERIFY {target.name}", flush=True)
    with candidate.open("rb") as source:
        actual = hashlib.file_digest(source, "sha256").hexdigest()
    if actual != item["sha256"]:
        raise RuntimeError(f"SHA256 mismatch for {target.name}: {actual}")
    if candidate != target:
        os.replace(candidate, target)
    receipt = {**item, "verified_sha256": actual, "completed_at": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
    receipt_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    print(f"READY {target}", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args()
    for artifact in json.loads(args.manifest.read_text(encoding="utf-8-sig")):
        download(artifact)
