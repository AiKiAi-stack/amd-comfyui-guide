"""Sync completed FLUX.2 Klein cases into the existing feature gallery.

This script is intentionally separate from the GPU runner. Run it only after
the desired case result files and reviews have settled:

    python trials/2026-10-20-flux2-klein/sync_gallery.py

It reads the current trial metadata at runtime, skips missing and in-progress
results, and never deletes existing case folders, images, or unrelated review
entries. The report itself is rebuilt separately with the existing
trials/2026-10-19-features/build_report.py.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import tempfile
from pathlib import Path


HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parents[1]
GALLERY = PROJECT_ROOT / "trials" / "2026-10-19-features"
CASE_FILES = ("api.json", "history.json", "submission.json", "result.json")
NONTERMINAL_STATUSES = {
    "pending",
    "queued",
    "submitted",
    "running",
    "processing",
    "in_progress",
}
SAFE_CASE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*\Z")


def snapshot_json(path: Path, *, optional: bool = False):
    """Read JSON once and detect a concurrent rewrite during the read."""
    try:
        before = path.stat()
    except FileNotFoundError:
        if optional:
            return None, None
        raise

    raw = path.read_bytes()
    after = path.stat()
    signature_before = (before.st_size, before.st_mtime_ns)
    signature_after = (after.st_size, after.st_mtime_ns)
    if signature_before != signature_after:
        raise RuntimeError(f"文件在读取时发生变化，请稍后再运行：{path}")
    try:
        return json.loads(raw.decode("utf-8-sig")), signature_after
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"JSON 无法读取：{path}：{exc}") from exc


def ensure_unchanged(path: Path, signature) -> None:
    """Avoid replacing destination metadata changed by another process."""
    try:
        stat = path.stat()
    except FileNotFoundError:
        current = None
    else:
        current = (stat.st_size, stat.st_mtime_ns)
    if current != signature:
        raise RuntimeError(f"目标文件在同步期间发生变化，未覆盖：{path}")


def safe_case_id(value) -> str:
    case_id = str(value or "")
    if not SAFE_CASE_ID.fullmatch(case_id):
        raise RuntimeError(f"不安全或缺失的 case id：{case_id!r}")
    return case_id


def terminal_result(record: dict) -> bool:
    status = str(record.get("status", "")).strip().lower()
    if status in NONTERMINAL_STATUSES:
        return False
    if status:
        return True
    # Some older result records omit status but still document a real attempt.
    return any(record.get(key) for key in ("prompt_id", "images", "errors", "error"))


def actionable_review(review) -> bool:
    if review in (None, "", "pending", "待评估", "尚未进行视觉检查"):
        return False
    if isinstance(review, dict):
        verdict = str(review.get("verdict") or review.get("status") or "").strip().lower()
        return bool(review) and verdict not in {
            "pending",
            "待评估",
            "尚未进行视觉检查",
        }
    return True


def write_json_atomic(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as stream:
            temp_path = Path(stream.name)
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        os.replace(temp_path, path)
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink()


def copy_case_artifacts(case_id: str) -> list[str]:
    source_dir = HERE / "cases" / case_id
    destination_dir = GALLERY / "cases" / case_id
    if not (source_dir / "result.json").is_file():
        raise RuntimeError(f"同步前 result.json 消失：{source_dir}")

    destination_dir.mkdir(parents=True, exist_ok=True)
    missing = []
    for filename in CASE_FILES:
        source = source_dir / filename
        if not source.is_file():
            if filename == "result.json":
                raise RuntimeError(f"缺少必要结果文件：{source}")
            missing.append(filename)
            continue
        shutil.copy2(source, destination_dir / filename)
    return missing


def model_fingerprint(value) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value or "").lower())


def assert_no_model_collision(existing: dict | None, incoming: dict, case_id: str) -> None:
    if existing is None:
        return
    old_model = model_fingerprint(existing.get("model"))
    new_model = model_fingerprint(incoming.get("model"))
    if old_model and new_model and old_model != new_model:
        if old_model not in new_model and new_model not in old_model:
            raise RuntimeError(
                f"case id {case_id!r} 已属于不同模型 "
                f"({existing.get('model')!r} vs {incoming.get('model')!r})，为保护旧数据已停止。"
            )


def main() -> int:
    source_cases, _ = snapshot_json(HERE / "cases.json")
    source_reviews, _ = snapshot_json(HERE / "reviews.json", optional=True)
    gallery_cases, gallery_cases_signature = snapshot_json(GALLERY / "cases.json")
    gallery_reviews, gallery_reviews_signature = snapshot_json(
        GALLERY / "reviews.json", optional=True
    )

    if not isinstance(source_cases, list):
        raise RuntimeError("新试验 cases.json 应为数组。")
    if source_reviews is None:
        source_reviews = {}
    if not isinstance(source_reviews, dict):
        raise RuntimeError("新试验 reviews.json 应为对象。")
    if not isinstance(gallery_cases, list):
        raise RuntimeError("旧报告 cases.json 应为数组。")
    if gallery_reviews is None:
        gallery_reviews = {}
    if not isinstance(gallery_reviews, dict):
        raise RuntimeError("旧报告 reviews.json 应为对象。")

    source_by_id: dict[str, dict] = {}
    for item in source_cases:
        if not isinstance(item, dict):
            continue
        case_id = safe_case_id(item.get("id"))
        if case_id in source_by_id:
            raise RuntimeError(f"新试验 cases.json 中 id 重复：{case_id}")
        source_by_id[case_id] = item

    gallery_by_id: dict[str, dict] = {}
    for item in gallery_cases:
        if isinstance(item, dict) and item.get("id") is not None:
            gallery_by_id[str(item["id"])] = item

    selected: list[tuple[str, dict, dict]] = []
    skipped: list[tuple[str, str]] = []
    for case_id, case in source_by_id.items():
        result_path = HERE / "cases" / case_id / "result.json"
        if not result_path.is_file():
            skipped.append((case_id, "没有 result.json"))
            continue
        result, _ = snapshot_json(result_path)
        if not isinstance(result, dict):
            raise RuntimeError(f"结果文件应为 JSON 对象：{result_path}")
        result_id = result.get("id")
        if result_id not in (None, "", case_id):
            raise RuntimeError(f"结果文件 id 与目录不一致：{result_path}")
        if not terminal_result(result):
            skipped.append((case_id, f"结果仍在运行（{result.get('status') or '未标状态'}）"))
            continue

        merged_case = dict(case)
        for field in ("model", "feature", "runtime_profile"):
            actual = result.get(field)
            if actual not in (None, ""):
                merged_case[field] = actual
        merged_case["id"] = case_id
        assert_no_model_collision(gallery_by_id.get(case_id), merged_case, case_id)
        selected.append((case_id, merged_case, result))

    if not selected:
        print("没有可同步的已完成案例；旧报告数据未改动。")
        for case_id, reason in skipped:
            print(f"跳过 {case_id}: {reason}")
        return 0

    # Copy evidence first; only publish JSON entries after every selected case
    # has its result bundle in the gallery tree. Extra destination files remain.
    missing_artifacts: dict[str, list[str]] = {}
    for case_id, _, _ in selected:
        missing = copy_case_artifacts(case_id)
        if missing:
            missing_artifacts[case_id] = missing

    updated_cases = list(gallery_cases)
    indices = {
        str(item["id"]): index
        for index, item in enumerate(updated_cases)
        if isinstance(item, dict) and item.get("id") is not None
    }
    updated_reviews = dict(gallery_reviews)
    for case_id, case, result in selected:
        if case_id in indices:
            merged = dict(updated_cases[indices[case_id]])
            merged.update(case)
            updated_cases[indices[case_id]] = merged
        else:
            indices[case_id] = len(updated_cases)
            updated_cases.append(case)

        review = source_reviews.get(case_id)
        if actionable_review(review):
            updated_reviews[case_id] = review

    ensure_unchanged(GALLERY / "cases.json", gallery_cases_signature)
    ensure_unchanged(GALLERY / "reviews.json", gallery_reviews_signature)
    write_json_atomic(GALLERY / "cases.json", updated_cases)
    write_json_atomic(GALLERY / "reviews.json", updated_reviews)

    print(f"已同步 {len(selected)} 个 FLUX.2 Klein 案例；旧案例及输出图片未删除。")
    for case_id, _, result in selected:
        image_count = len(result.get("images", [])) if isinstance(result.get("images"), list) else 0
        elapsed = result.get("elapsed_seconds", result.get("elapsed"))
        batch_elapsed = result.get("batch_elapsed_seconds")
        timing = f"耗时 {elapsed} 秒" if elapsed is not None else "耗时未记录"
        if batch_elapsed is not None:
            timing = f"批次耗时 {batch_elapsed} 秒（非单项）"
        print(
            f"- {case_id}: status={result.get('status', '未标状态')}, "
            f"images={image_count}, {timing}"
        )
        if case_id in missing_artifacts:
            print(f"  缺少可选证据文件：{', '.join(missing_artifacts[case_id])}")
    for case_id, reason in skipped:
        print(f"跳过 {case_id}: {reason}")
    print(
        "请在父代理确认同步后运行："
        "python trials/2026-10-19-features/build_report.py"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
