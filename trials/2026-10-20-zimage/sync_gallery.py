"""Import completed Z-Image evidence into the shared feature gallery.

Run only after the desired cases have terminal result.json records:

    python trials/2026-10-20-zimage/sync_gallery.py

The script copies the runner's original api/submission/history/result JSON and
keeps its real ComfyUI image paths and image metadata. It never uses prepared
workflows as results. Rebuild the report separately with
trials/2026-10-19-features/build_report.py.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parents[1]
GALLERY = PROJECT_ROOT / "trials" / "2026-10-19-features"
COMFY_ROOT = PROJECT_ROOT / "ComfyUI"
COMFY_OUTPUT = COMFY_ROOT / "output"
ARTIFACTS = ("api.json", "submission.json", "history.json", "result.json")
TERMINAL_STATUSES = {"success", "error", "interrupted", "failed"}
SAFE_CASE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*\Z")


def snapshot_json(path: Path, *, optional: bool = False):
    """Read JSON once and return its signature and original bytes."""
    try:
        before = path.stat()
    except FileNotFoundError:
        if optional:
            return None, None, None
        raise
    raw = path.read_bytes()
    after = path.stat()
    signature_before = (before.st_size, before.st_mtime_ns)
    signature_after = (after.st_size, after.st_mtime_ns)
    if signature_before != signature_after:
        raise RuntimeError(f"文件在读取时发生变化，请稍后重试：{path}")
    try:
        value = json.loads(raw.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"JSON 无法读取：{path}：{exc}") from exc
    return value, signature_after, raw


def ensure_unchanged(path: Path, signature) -> None:
    try:
        stat = path.stat()
    except FileNotFoundError:
        current = None
    else:
        current = (stat.st_size, stat.st_mtime_ns)
    if current != signature:
        raise RuntimeError(f"文件在同步期间发生变化，未覆盖：{path}")


def safe_case_id(value: Any) -> str:
    case_id = str(value or "")
    if not SAFE_CASE_ID.fullmatch(case_id):
        raise RuntimeError(f"case id 不安全或缺失：{case_id!r}")
    return case_id


def indexed_cases(value: Any, label: str) -> tuple[list, dict[str, dict]]:
    if not isinstance(value, list):
        raise RuntimeError(f"{label} 顶层应为数组。")
    by_id: dict[str, dict] = {}
    for item in value:
        if not isinstance(item, dict):
            raise RuntimeError(f"{label} 中每项都应为对象。")
        case_id = safe_case_id(item.get("id"))
        if case_id in by_id:
            raise RuntimeError(f"{label} 中 id 重复：{case_id}")
        by_id[case_id] = item
    return value, by_id


def path_key(path: Path) -> str:
    return os.path.normcase(str(path.resolve()))


def history_image_paths(history: dict) -> list[Path]:
    outputs = history.get("outputs")
    if not isinstance(outputs, dict):
        raise RuntimeError("终态 history 缺少 outputs 对象。")
    found: list[Path] = []
    comfy_root = COMFY_ROOT.resolve()
    for output in outputs.values():
        if not isinstance(output, dict):
            continue
        images = output.get("images", [])
        if not isinstance(images, list):
            raise RuntimeError("history output.images 应为数组。")
        for image in images:
            if not isinstance(image, dict):
                raise RuntimeError("history 中的图片记录应为对象。")
            filename = image.get("filename")
            subfolder = image.get("subfolder", "")
            image_type = image.get("type", "output")
            if (
                not isinstance(filename, str)
                or not filename
                or Path(filename).name != filename
                or not isinstance(subfolder, str)
                or not isinstance(image_type, str)
            ):
                raise RuntimeError("history 图片路径字段无效。")
            image_path = (COMFY_ROOT / image_type / subfolder / filename).resolve()
            if not image_path.is_relative_to(comfy_root):
                raise RuntimeError(f"history 图片路径越出 ComfyUI 目录：{image_path}")
            found.append(image_path)
    return found


def validate_bundle(case_id: str, case: dict, bundle: dict[str, tuple[Any, Any, bytes]]):
    api, submission, history, result = (
        bundle[name][0] for name in ARTIFACTS
    )
    if not all(isinstance(item, dict) for item in (api, submission, history, result)):
        raise RuntimeError(f"{case_id}: api/submission/history/result 都应为 JSON 对象。")
    if result.get("id") != case_id:
        raise RuntimeError(f"{case_id}: result.json 的 id 与目录不符。")
    status = str(result.get("status", "")).strip().lower()
    history_status = history.get("status")
    history_status = (
        str(history_status.get("status_str", "")).strip().lower()
        if isinstance(history_status, dict)
        else ""
    )
    if status not in TERMINAL_STATUSES or status != history_status:
        raise RuntimeError(
            f"{case_id}: result/history 状态不匹配或非终态：{status!r}/{history_status!r}。"
        )
    prompt_id = result.get("prompt_id")
    if not isinstance(prompt_id, str) or not prompt_id:
        raise RuntimeError(f"{case_id}: result.json 缺少真实 prompt_id。")
    submitted_id = submission.get("prompt_id")
    if submitted_id != prompt_id:
        raise RuntimeError(f"{case_id}: submission.json 与 result.json 的 prompt_id 不符。")

    history_prompt = history.get("prompt")
    if (
        not isinstance(history_prompt, list)
        or len(history_prompt) < 3
        or history_prompt[1] != prompt_id
        or history_prompt[2] != api
    ):
        raise RuntimeError(f"{case_id}: history 中的已执行 graph 与 api.json 不符。")

    if result.get("model") != case.get("model"):
        raise RuntimeError(f"{case_id}: result.json 的模型与试验定义不符。")
    if result.get("feature") != case.get("feature"):
        raise RuntimeError(f"{case_id}: result.json 的功能名与试验定义不符。")
    runtime_profile = result.get("runtime_profile")
    if not isinstance(runtime_profile, str) or not runtime_profile.strip():
        raise RuntimeError(f"{case_id}: 缺少运行器记录的实际 runtime_profile。")

    planned_prompt_node = case.get("prompt_node")
    prompt_node = api.get(str(planned_prompt_node))
    prompt_inputs = prompt_node.get("inputs") if isinstance(prompt_node, dict) else None
    prompt_field = next(
        (name for name in ("text", "prompt") if isinstance(prompt_inputs, dict) and name in prompt_inputs),
        None,
    )
    if prompt_field is None or prompt_inputs[prompt_field] != case.get("prompt"):
        raise RuntimeError(f"{case_id}: api.json 实际提交的提示词与试验定义不符。")

    raw_images = result.get("images")
    metadata = result.get("image_metadata")
    if not isinstance(raw_images, list) or not isinstance(metadata, list):
        raise RuntimeError(f"{case_id}: result.json 的 images/image_metadata 应为数组。")
    history_paths = history_image_paths(history)
    result_paths: list[Path] = []
    for image in raw_images:
        if not isinstance(image, str) or not image:
            raise RuntimeError(f"{case_id}: result.json 含无效 image 路径。")
        path = Path(image).resolve()
        if not path.is_relative_to(COMFY_OUTPUT.resolve()):
            raise RuntimeError(f"{case_id}: 输出图片不在 ComfyUI/output：{path}")
        result_paths.append(path)
    if [path_key(path) for path in result_paths] != [path_key(path) for path in history_paths]:
        raise RuntimeError(f"{case_id}: result.json 图片路径与终态 history 不一致。")
    if len(metadata) != len(result_paths):
        raise RuntimeError(f"{case_id}: image_metadata 数量与实际 history 图片数不符。")
    for path, item in zip(result_paths, metadata, strict=True):
        if not isinstance(item, dict) or path_key(Path(str(item.get("path", "")))) != path_key(path):
            raise RuntimeError(f"{case_id}: 图片 metadata 路径与实际图片不符。")
        if path.is_file():
            expected_hash = item.get("sha256")
            if expected_hash:
                actual_hash = hashlib.sha256(path.read_bytes()).hexdigest()
                if actual_hash.lower() != str(expected_hash).lower():
                    raise RuntimeError(f"{case_id}: 图片 SHA-256 与 result metadata 不符：{path}")
            elif not item.get("inspection_error"):
                raise RuntimeError(f"{case_id}: 现存输出图片没有 SHA-256 或 inspection_error：{path}")
        elif status == "success":
            raise RuntimeError(f"{case_id}: success 结果引用的输出图片不存在：{path}")
    if status == "success" and not result_paths:
        raise RuntimeError(f"{case_id}: success 结果没有来自 history 的输出图片。")


def write_bytes_atomic(path: Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False
        ) as stream:
            temp_path = Path(stream.name)
            stream.write(raw)
        os.replace(temp_path, path)
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink()


def write_json_atomic(path: Path, value: Any) -> None:
    raw = (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    write_bytes_atomic(path, raw)


def is_pending_review(value: Any) -> bool:
    if value in (None, "", "pending", "待评估", "尚未进行视觉检查"):
        return True
    if isinstance(value, dict):
        verdict = str(value.get("verdict") or value.get("status") or "").strip().lower()
        return verdict in {"", "pending", "待评估", "尚未进行视觉检查"}
    return False


def remove_imported_blockers(value: Any, selected_ids: set[str], label: str) -> list:
    if not isinstance(value, list):
        raise RuntimeError(f"{label} 顶层应为数组。")
    return [
        item for item in value
        if not (isinstance(item, dict) and str(item.get("id", "")) in selected_ids)
    ]


def main() -> int:
    source_cases_value, source_cases_sig, _ = snapshot_json(HERE / "cases.json")
    source_cases, source_by_id = indexed_cases(source_cases_value, "Z-Image cases.json")
    source_reviews, source_reviews_sig, _ = snapshot_json(
        HERE / "reviews.json", optional=True
    )
    if source_reviews is None:
        source_reviews = {}
    if not isinstance(source_reviews, dict):
        raise RuntimeError("Z-Image reviews.json 顶层应为对象。")

    gallery_cases, gallery_cases_sig, _ = snapshot_json(GALLERY / "cases.json")
    gallery_cases, gallery_by_id = indexed_cases(gallery_cases, "features cases.json")
    gallery_reviews, gallery_reviews_sig, _ = snapshot_json(
        GALLERY / "reviews.json", optional=True
    )
    if gallery_reviews is None:
        gallery_reviews = {}
    if not isinstance(gallery_reviews, dict):
        raise RuntimeError("features reviews.json 顶层应为对象。")
    gallery_blocked, gallery_blocked_sig, _ = snapshot_json(GALLERY / "blocked.json")
    source_blocked, source_blocked_sig, _ = snapshot_json(
        HERE / "blocked.json", optional=True
    )
    if source_blocked is None:
        source_blocked = []

    source_case_root = HERE / "cases"
    result_paths = sorted(source_case_root.glob("*/result.json")) if source_case_root.is_dir() else []
    selected: list[tuple[str, dict, dict[str, tuple[Any, Any, bytes]]]] = []
    skipped: list[tuple[str, str]] = []
    for result_path in result_paths:
        case_id = safe_case_id(result_path.parent.name)
        if case_id not in source_by_id:
            raise RuntimeError(f"有 result.json 的目录不在 Z-Image cases.json 中：{case_id}")
        bundle: dict[str, tuple[Any, Any, bytes]] = {}
        for filename in ARTIFACTS:
            bundle[filename] = snapshot_json(result_path.parent / filename)
        result = bundle["result.json"][0]
        if not isinstance(result, dict):
            raise RuntimeError(f"result.json 应为对象：{result_path}")
        status = str(result.get("status", "")).strip().lower()
        if status not in TERMINAL_STATUSES:
            skipped.append((case_id, f"非终态（{status or '未标状态'}）"))
            continue
        validate_bundle(case_id, source_by_id[case_id], bundle)
        selected.append((case_id, source_by_id[case_id], bundle))

    if not selected:
        print("没有可同步的真实终态 Z-Image 案例；gallery 与 blocked 清单未改动。")
        for case_id, reason in skipped:
            print(f"跳过 {case_id}: {reason}")
        return 0

    selected_ids = {case_id for case_id, _, _ in selected}
    updated_cases = list(gallery_cases)
    updated_indices = {
        str(item["id"]): index
        for index, item in enumerate(updated_cases)
        if isinstance(item, dict) and item.get("id") is not None
    }
    updated_reviews = dict(gallery_reviews)

    # Preflight every ID and every destination file before copying anything.
    for case_id, case, bundle in selected:
        for filename in ARTIFACTS:
            ensure_unchanged(
                HERE / "cases" / case_id / filename,
                bundle[filename][1],
            )
        existing = gallery_by_id.get(case_id)
        if existing is not None:
            for field in ("model", "feature", "recipe", "prompt", "expected"):
                old, new = existing.get(field), case.get(field)
                if old not in (None, "") and new not in (None, "") and old != new:
                    raise RuntimeError(
                        f"case id {case_id!r} 的 {field} 与 gallery 记录冲突，已停止。"
                    )
        destination = GALLERY / "cases" / case_id
        if not destination.resolve().is_relative_to((GALLERY / "cases").resolve()):
            raise RuntimeError(f"目标案例路径越出 gallery：{destination}")
        for filename in ARTIFACTS:
            target = destination / filename
            raw = bundle[filename][2]
            if target.exists() and target.read_bytes() != raw:
                raise RuntimeError(f"目标证据已存在且内容不同，未覆盖：{target}")

    # Publish immutable run evidence first; JSON indexes follow only when every
    # copied bundle is present. Original result paths and metadata stay intact.
    for case_id, _, bundle in selected:
        destination = GALLERY / "cases" / case_id
        for filename in ARTIFACTS:
            target = destination / filename
            if not target.exists():
                write_bytes_atomic(target, bundle[filename][2])

    for case_id, case, bundle in selected:
        result = bundle["result.json"][0]
        merged_case = dict(case)
        planned_profile = result.get("planned_runtime_profile")
        if planned_profile not in (None, ""):
            merged_case["planned_runtime_profile"] = planned_profile
        merged_case["runtime_profile"] = result["runtime_profile"]
        # Results live in the per-case evidence bundle; the gallery index stays
        # a case definition and does not invent or duplicate output records.
        for field in ("status", "reason", "evidence", "images", "image_metadata", "elapsed_seconds"):
            merged_case.pop(field, None)
        index = updated_indices.get(case_id)
        if index is None:
            updated_indices[case_id] = len(updated_cases)
            updated_cases.append(merged_case)
        else:
            combined = dict(updated_cases[index])
            combined.update(merged_case)
            updated_cases[index] = combined

        new_review = source_reviews.get(case_id)
        old_review = updated_reviews.get(case_id)
        if is_pending_review(new_review):
            if case_id not in updated_reviews or is_pending_review(old_review):
                updated_reviews[case_id] = "pending"
        else:
            updated_reviews[case_id] = new_review

    updated_gallery_blocked = remove_imported_blockers(
        gallery_blocked, selected_ids, "features blocked.json"
    )
    updated_source_blocked = remove_imported_blockers(
        source_blocked, selected_ids, "Z-Image blocked.json"
    )

    # Abort on concurrent metadata edits instead of replacing newer data.
    ensure_unchanged(GALLERY / "cases.json", gallery_cases_sig)
    ensure_unchanged(GALLERY / "reviews.json", gallery_reviews_sig)
    ensure_unchanged(GALLERY / "blocked.json", gallery_blocked_sig)
    ensure_unchanged(HERE / "cases.json", source_cases_sig)
    ensure_unchanged(HERE / "reviews.json", source_reviews_sig)
    ensure_unchanged(HERE / "blocked.json", source_blocked_sig)
    write_json_atomic(GALLERY / "cases.json", updated_cases)
    write_json_atomic(GALLERY / "reviews.json", updated_reviews)
    write_json_atomic(GALLERY / "blocked.json", updated_gallery_blocked)
    if source_blocked_sig is not None:
        write_json_atomic(HERE / "blocked.json", updated_source_blocked)

    print(f"已同步 {len(selected)} 个 Z-Image 终态案例；原输出路径与 image_metadata 已保留。")
    for case_id, _, bundle in selected:
        result = bundle["result.json"][0]
        count = len(result.get("images", []))
        print(
            f"- {case_id}: status={result['status']}, images={count}, "
            f"output_validation={result.get('output_validation_status', '未记录')}"
        )
    for case_id, reason in skipped:
        print(f"跳过 {case_id}: {reason}")
    print("若要更新离线报告，再运行：python trials/2026-10-19-features/build_report.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
