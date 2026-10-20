import json
from datetime import datetime
from pathlib import Path
import shutil

HERE = Path(__file__).resolve().parent
path = HERE / "cases.json"
cases = json.loads(path.read_text(encoding="utf-8"))
archive_root = HERE / "attempts" / ("kroma-ref1024-" + datetime.now().strftime("%Y%m%d-%H%M%S"))
for case in cases:
    if case["model"] != "kroma" or case["recipe"] != "reference":
        continue
    source = HERE / "cases" / case["id"]
    result = source / "result.json"
    if result.exists():
        previous = json.loads(result.read_text(encoding="utf-8"))
        if previous.get("status") == "success":
            raise RuntimeError("Refusing to archive a successful case")
        destination = archive_root / case["id"]
        source.resolve().relative_to((HERE / "cases").resolve())
        destination.resolve().relative_to((HERE / "attempts").resolve())
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source), str(destination))
        case["prior_attempt_evidence"] = str((destination / "result.json").relative_to(HERE))
    case["reference_vae_resolution"] = 512
    case["retry_reason"] = "原始 1024 参考批次反复 softmax 显存不足，随后 Fatal Python error: Aborted，无图片。保留该次证据后，使用核心 ReferenceLatent 节点改为 512 参考重试。"
path.write_text(json.dumps(cases, ensure_ascii=False, indent=2), encoding="utf-8")
print("Prepared 512 reference retry; previous evidence:", archive_root)
