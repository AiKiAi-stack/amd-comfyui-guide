"""Apply the narrow uneven-query split fix to an existing ComfyUI checkout."""
import argparse
import hashlib
import json
from pathlib import Path

OLD = b"slice_size = q.shape[1] // steps if (q.shape[1] % steps) == 0 else q.shape[1]"
NEW = b"slice_size = max(1, (q.shape[1] + steps - 1) // steps)"


def patch_bytes(source):
    if source.count(NEW) == 1 and OLD not in source:
        return source
    if source.count(OLD) != 1 or NEW in source:
        raise ValueError("Unrecognized attention source; refusing an ambiguous patch")
    return source.replace(OLD, NEW, 1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime", type=Path, required=True)
    parser.add_argument("--record", type=Path, required=True)
    args = parser.parse_args()
    target = args.runtime.resolve() / "ComfyUI/comfy/ldm/modules/attention.py"
    before = target.read_bytes()
    after = patch_bytes(before)
    compile(after, str(target), "exec")
    args.record.parent.mkdir(parents=True, exist_ok=True)
    if after == before and args.record.exists():
        print("Already applied; existing patch record preserved")
        return
    if after != before:
        backup = args.record.with_suffix(".original.py")
        if backup.exists():
            raise FileExistsError("Keep the existing patch evidence; select a new record path")
        backup.write_bytes(before)
        target.write_bytes(after)
    args.record.write_text(json.dumps({"file": "ComfyUI/comfy/ldm/modules/attention.py",
        "changed": before != after, "before_sha256": hashlib.sha256(before).hexdigest(),
        "after_sha256": hashlib.sha256(after).hexdigest()}, indent=2), encoding="utf-8")
    print("Applied uneven-query split fix" if before != after else "Already applied")


if __name__ == "__main__":
    main()
