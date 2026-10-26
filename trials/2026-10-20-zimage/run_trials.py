"""Run recorded Z-Image API workflows one case at a time.

This runner requires a recent healthy GPU probe and an idle ComfyUI API before
the first submission. It preserves the submitted graph and API history, and
creates result.json only after a terminal history entry exists. Pending cases
default to memory_profile=legacy-lowvram; mixed profiles require --case.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shlex
import struct
import time
import urllib.error
import urllib.parse
import urllib.request
import zlib
import psutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parents[1]
GPU_PROBES = PROJECT_ROOT / "trials" / "2026-10-20-flux2-klein" / "gpu-probes"
DEFAULT_BASE_URL = "http://127.0.0.1:8188"
SAFE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*\Z")
PROBE_DIR_STAMP = re.compile(r"\d{8}T\d{6}Z\Z")
TERMINAL_STATUSES = {"success", "error", "interrupted", "failed"}
PROBE_MAX_AGE_SECONDS = 300
DEFAULT_RUN_TIMEOUT = 2400
MEMORY_PROFILES = {
    "dynamic-nvme": {
        "opposite_mode_flag": "--disable-dynamic-vram",
        "flags": (
            "--enable-dynamic-vram", "--fast-disk", "--disable-pinned-memory",
            "--cpu-vae", "--disable-async-offload",
        ),
    },
    "legacy-lowvram": {
        "opposite_mode_flag": "--gpu-only",
        "flags": (
            "--disable-dynamic-vram",
            "--lowvram",
            "--cpu-vae",
            "--disable-async-offload",
        ),
    },
    "legacy-normalvram": {
        "opposite_mode_flag": "--lowvram",
        "flags": (
            "--disable-dynamic-vram",
            "--cpu-vae",
            "--disable-async-offload",
        ),
    },
}


class RunnerError(RuntimeError):
    """A safe preflight or recorded-case failure."""


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def api_request(base_url: str, path: str, *, method: str = "GET", body: Any = None,
                timeout: int = 30) -> tuple[int, Any, str]:
    url = base_url.rstrip("/") + path
    data = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
    headers = {"Accept": "application/json"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read()
            status = response.status
    except urllib.error.HTTPError as error:
        raw = error.read()
        status = error.code
    text = raw.decode("utf-8", errors="replace")
    try:
        parsed = json.loads(text) if text else None
    except json.JSONDecodeError:
        parsed = None
    return status, parsed, text


def parse_probe_time(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    if PROBE_DIR_STAMP.fullmatch(value):
        return datetime.strptime(value, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def require_fresh_healthy_probe(now: datetime | None = None) -> dict[str, Any]:
    now = now or datetime.now(timezone.utc)
    if not GPU_PROBES.is_dir():
        raise RunnerError(f"找不到 GPU probe 目录：{GPU_PROBES}")

    candidates: list[tuple[datetime, Path]] = []
    for folder in GPU_PROBES.iterdir():
        if not folder.is_dir():
            continue
        stamp = parse_probe_time(folder.name)
        if stamp is None and (folder / "result.json").is_file():
            try:
                result = json.loads((folder / "result.json").read_text(encoding="utf-8-sig"))
            except (OSError, json.JSONDecodeError):
                result = None
            if isinstance(result, dict):
                stamp = parse_probe_time(result.get("timestamp"))
        if stamp is not None:
            candidates.append((stamp, folder))

    if not candidates:
        raise RunnerError(f"没有可识别时间戳的 GPU probe：{GPU_PROBES}")
    latest_time, latest_folder = max(candidates, key=lambda item: item[0])
    latest_result_path = latest_folder / "result.json"
    if not latest_result_path.is_file():
        raise RunnerError(f"最新 GPU probe 尚无 result.json：{latest_folder}")
    try:
        latest = json.loads(latest_result_path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as error:
        raise RunnerError(f"最新 GPU probe 结果不可读：{latest_result_path}: {error}") from error
    if not isinstance(latest, dict):
        raise RunnerError(f"最新 GPU probe 结果格式错误：{latest_result_path}")
    if latest.get("healthy") is not True:
        raise RunnerError(
            f"最新 GPU probe 未通过（healthy={latest.get('healthy')!r}）：{latest_folder}；"
            "本次不提交任何 ComfyUI prompt。"
        )
    completed_time = parse_probe_time(latest.get('completed_at')) or datetime.fromtimestamp(latest_result_path.stat().st_mtime,timezone.utc)
    age = (now - completed_time).total_seconds()
    if age < 0 or age > PROBE_MAX_AGE_SECONDS:
        raise RunnerError(
            f"最新 GPU probe 已过期或时间在未来（age={age:.1f}s，要求 0–"
            f"{PROBE_MAX_AGE_SECONDS}s）：{latest_folder}"
        )
    result_time = parse_probe_time(latest.get("timestamp"))
    if result_time is not None and abs((result_time - latest_time).total_seconds()) > 60:
        raise RunnerError(f"GPU probe 目录时间与 result.json 不一致：{latest_folder}")
    return {
        "path": str(latest_result_path),
        "timestamp": latest_time.isoformat(),
        "age_seconds": round(age, 2),
        "healthy": True,
    }


def safe_case_id(value: Any) -> str:
    case_id = str(value or "")
    if not SAFE_ID.fullmatch(case_id):
        raise RunnerError(f"case id 不安全或缺失：{case_id!r}")
    return case_id


def case_workflow_path(value: Any) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise RunnerError("workflow_api 必须是相对 trials/2026-10-20-zimage 的路径。")
    candidate = Path(value)
    if candidate.is_absolute():
        raise RunnerError(f"workflow_api 必须使用相对路径：{value}")
    path = (HERE / candidate).resolve()
    if not path.is_relative_to(HERE):
        raise RunnerError(f"workflow_api 不能离开 trial 目录：{value}")
    return path


def node_for(graph: dict[str, Any], node_id: Any, field: str) -> dict[str, Any]:
    key = str(node_id)
    node = graph.get(key)
    if not isinstance(node, dict) or not isinstance(node.get("inputs"), dict):
        raise RunnerError(f"{field}={node_id!r} 不在 workflow_api 节点中。")
    return node


def set_dimension_node(graph: dict[str, Any], case: dict[str, Any]) -> None:
    width, height = case.get("width"), case.get("height")
    if width is None and height is None:
        return
    if not isinstance(width, int) or not isinstance(height, int) or width <= 0 or height <= 0:
        raise RunnerError(f"{case['id']}: width/height 必须同时是正整数。")

    latent_id = case.get("latent_node")
    if latent_id not in (None, ""):
        node = node_for(graph, latent_id, "latent_node")
    else:
        matches = [
            item for item in graph.values()
            if isinstance(item, dict)
            and isinstance(item.get("inputs"), dict)
            and "width" in item["inputs"]
            and "height" in item["inputs"]
        ]
        if len(matches) != 1:
            raise RunnerError(
                f"{case['id']}: 找到 {len(matches)} 个宽高节点，请在 case 中指定 latent_node。"
            )
        node = matches[0]
    if "width" not in node["inputs"] or "height" not in node["inputs"]:
        raise RunnerError(f"{case['id']}: latent_node 必须具有 width 和 height 输入。")
    node["inputs"]["width"] = width
    node["inputs"]["height"] = height


def build_graph(case: dict[str, Any]) -> dict[str, Any]:
    case_id = safe_case_id(case.get("id"))
    workflow_path = case_workflow_path(case.get("workflow_api"))
    try:
        graph = json.loads(workflow_path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as error:
        raise RunnerError(f"{case_id}: 无法读取 workflow_api {workflow_path}: {error}") from error
    if not isinstance(graph, dict) or not graph:
        raise RunnerError(f"{case_id}: workflow_api 必须是非空 API prompt 对象。")
    for node_id, node in graph.items():
        if not isinstance(node, dict) or not isinstance(node.get("class_type"), str) \
                or not isinstance(node.get("inputs"), dict):
            raise RunnerError(f"{case_id}: API 节点 {node_id!r} 缺少 class_type 或 inputs。")

    prompt_node = node_for(graph, case.get("prompt_node"), "prompt_node")
    prompt_field = next(
        (field for field in ("text", "prompt") if field in prompt_node["inputs"]),
        None,
    )
    if not isinstance(case.get("prompt"), str) or prompt_field is None:
        raise RunnerError(
            f"{case_id}: prompt 必须是字符串，prompt_node 必须有 text 或 prompt 输入。"
        )
    prompt_node["inputs"][prompt_field] = case["prompt"]

    sampler = node_for(graph, case.get("sampler_node"), "sampler_node")
    sampler_inputs = sampler["inputs"]
    seed_key = "seed" if "seed" in sampler_inputs else "noise_seed" if "noise_seed" in sampler_inputs else None
    if seed_key is None or "steps" not in sampler_inputs:
        raise RunnerError(f"{case_id}: sampler_node 需要 seed/noise_seed 和 steps 输入。")
    if not isinstance(case.get("seed"), int) or not isinstance(case.get("steps"), int):
        raise RunnerError(f"{case_id}: seed 和 steps 必须是整数。")
    sampler_inputs[seed_key] = case["seed"]
    sampler_inputs["steps"] = case["steps"]

    save_node = node_for(graph, case.get("save_node"), "save_node")
    if "filename_prefix" not in save_node["inputs"]:
        raise RunnerError(f"{case_id}: save_node 缺少 filename_prefix 输入。")
    save_node["inputs"]["filename_prefix"] = f"FeatureBench/{case_id}"
    set_dimension_node(graph, case)
    return graph


def png_text_chunks(path: Path) -> dict[str, list[str]]:
    """Read PNG tEXt, zTXt and iTXt metadata using only the standard library."""
    signature = b"\x89PNG\r\n\x1a\n"
    metadata: dict[str, list[str]] = {}
    with path.open("rb") as image_file:
        if image_file.read(8) != signature:
            raise ValueError("not a PNG file")
        while True:
            header = image_file.read(8)
            if len(header) != 8:
                raise ValueError("truncated PNG chunk header")
            size, kind = struct.unpack(">I4s", header)
            payload = image_file.read(size)
            crc = image_file.read(4)
            if len(payload) != size or len(crc) != 4:
                raise ValueError("truncated PNG chunk")
            text = decode_png_text(kind, payload)
            if text is not None:
                key, value = text
                metadata.setdefault(key, []).append(value)
            if kind == b"IEND":
                break
    return metadata


def decode_png_text(kind: bytes, payload: bytes) -> tuple[str, str] | None:
    try:
        if kind == b"tEXt":
            key, value = payload.split(b"\0", 1)
            return key.decode("latin-1"), value.decode("latin-1")
        if kind == b"zTXt":
            key, rest = payload.split(b"\0", 1)
            if not rest or rest[0] != 0:
                return None
            return key.decode("latin-1"), zlib.decompress(rest[1:]).decode("latin-1")
        if kind == b"iTXt":
            key, rest = payload.split(b"\0", 1)
            compressed, rest = rest[0], rest[1:]
            method, rest = rest[0], rest[1:]
            _language, rest = rest.split(b"\0", 1)
            _translated, value = rest.split(b"\0", 1)
            if compressed:
                if method != 0:
                    return None
                value = zlib.decompress(value)
            return key.decode("latin-1"), value.decode("utf-8", errors="replace")
    except (ValueError, IndexError, zlib.error):
        return None
    return None


def png_dimensions(path: Path) -> tuple[int, int]:
    with path.open("rb") as image_file:
        header = image_file.read(24)
    if len(header) < 24 or header[:8] != b"\x89PNG\r\n\x1a\n" or header[12:16] != b"IHDR":
        raise ValueError("PNG IHDR is missing or invalid")
    return struct.unpack(">II", header[16:24])


def prompt_from_png_metadata(metadata: dict[str, list[str]], prompt_node_id: Any,
                             prompt_field: str, expected_prompt: str) -> dict[str, Any]:
    values = metadata.get("prompt", [])
    node_id = str(prompt_node_id)
    for raw in values:
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict) and isinstance(payload.get("prompt"), dict):
            payload = payload["prompt"]
        if isinstance(payload, dict):
            node = payload.get(node_id)
            if isinstance(node, dict) and isinstance(node.get("inputs"), dict):
                actual = node["inputs"].get(prompt_field)
                return {
                    "status": "matched" if actual == expected_prompt else "mismatch",
                    "node_id": node_id,
                    "input_field": prompt_field,
                    "actual_text": actual,
                }
    return {"status": "unavailable", "node_id": node_id, "input_field": prompt_field,
            "detail": "PNG 内无可解析的 prompt 元数据或指定节点。"}


def inspect_image(path: Path, prompt_node_id: Any, prompt_field: str,
                  expected_prompt: str) -> dict[str, Any]:
    record: dict[str, Any] = {"path": str(path)}
    try:
        width, height = png_dimensions(path)
        metadata = png_text_chunks(path)
        record.update(
            dimensions=[width, height],
            sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
            png_prompt_binding=prompt_from_png_metadata(
                metadata, prompt_node_id, prompt_field, expected_prompt
            ),
        )
    except (OSError, ValueError) as error:
        record["inspection_error"] = str(error)
    return record


def check_api_preflight(
    base_url: str,
    graphs: list[tuple[dict[str, Any], dict[str, Any]]],
    memory_profile: str,
) -> dict[str, Any]:
    status, queue, text = api_request(base_url, "/queue", timeout=15)
    if status != 200 or not isinstance(queue, dict):
        raise RunnerError(f"ComfyUI /queue GET 失败（HTTP {status}）：{text[:500]}")
    running = queue.get("queue_running")
    pending = queue.get("queue_pending")
    if not isinstance(running, list) or not isinstance(pending, list):
        raise RunnerError("ComfyUI /queue 响应缺少 queue_running/queue_pending；拒绝提交。")
    if running or pending:
        raise RunnerError(
            f"ComfyUI 当前非空闲（running={len(running)}, pending={len(pending)}）；拒绝提交。"
        )

    status, system_stats, text = api_request(base_url, "/system_stats", timeout=30)
    if status != 200 or not isinstance(system_stats, dict):
        raise RunnerError(f"ComfyUI /system_stats GET 失败（HTTP {status}）：{text[:500]}")
    system_profile = verify_system_profile(system_stats, memory_profile)

    status, object_info, text = api_request(base_url, "/object_info", timeout=60)
    if status != 200 or not isinstance(object_info, dict):
        raise RunnerError(f"ComfyUI /object_info GET 失败（HTTP {status}）：{text[:500]}")
    required_classes = sorted({
        node["class_type"]
        for _, graph in graphs
        for node in graph.values()
        if isinstance(node, dict) and isinstance(node.get("class_type"), str)
    })
    missing = [class_type for class_type in required_classes if class_type not in object_info]
    if missing:
        raise RunnerError(f"ComfyUI 缺少 workflow API 节点类：{', '.join(missing)}")
    return {
        "queue_idle": True,
        "queue_running": 0,
        "queue_pending": 0,
        "checked_api_node_classes": required_classes,
        "memory_profile": memory_profile,
        "system_stats": system_stats,
        "system_profile": system_profile,
        "runtime_profile": runtime_profile_from(system_profile),
    }


def argv_tokens(system: dict[str, Any]) -> list[str]:
    value = system.get("argv")
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return value
    if isinstance(value, str):
        try:
            return shlex.split(value, posix=False)
        except ValueError as error:
            raise RunnerError(f"/system_stats argv 无法解析：{error}") from error
    raise RunnerError("/system_stats 未提供可解析的 system.argv；拒绝提交。")


def verify_system_profile(
    system_stats: dict[str, Any], memory_profile: str
) -> dict[str, Any]:
    if memory_profile not in MEMORY_PROFILES:
        raise RunnerError(f"不支持的 memory_profile：{memory_profile!r}")
    system = system_stats.get("system")
    devices = system_stats.get("devices")
    if not isinstance(system, dict) or not isinstance(devices, list):
        raise RunnerError("/system_stats 缺少 system 或 devices；拒绝提交。")

    argv = argv_tokens(system)
    normalized_argv = [token.lower() for token in argv]
    profile = MEMORY_PROFILES[memory_profile]
    required_flags = profile["flags"]
    missing = [flag for flag in required_flags if flag not in normalized_argv]
    if profile["opposite_mode_flag"] in normalized_argv:
        missing.append(f"不应同时包含 {profile['opposite_mode_flag']}")
    reserve_value = None
    for index, token in enumerate(normalized_argv):
        if token.startswith("--reserve-vram="):
            reserve_value = token.split("=", 1)[1]
            break
        if token == "--reserve-vram" and index + 1 < len(normalized_argv):
            reserve_value = normalized_argv[index + 1]
            break
    try:
        reserve_ok = reserve_value is not None and float(reserve_value) == 2.0
    except ValueError:
        reserve_ok = False
    if not reserve_ok:
        missing.append("--reserve-vram 2.0")

    device = next(
        (
            item for item in devices
            if isinstance(item, dict)
            and "6650" in str(item.get("name", "")).lower()
        ),
        None,
    )
    if device is None:
        raise RunnerError("/system_stats 当前设备列表不含 RX 6650 XT；拒绝提交。")
    if missing:
        raise RunnerError(
            "/system_stats argv 缺少或未匹配要求的启动参数："
            + ", ".join(missing)
            + "；拒绝提交。"
        )

    return {
        "argv": argv,
        "device": device,
        "memory_profile": memory_profile,
        "verified_flags": [*required_flags, "--reserve-vram 2.0"],
        "versions": {
            key: system.get(key)
            for key in ("comfyui_version", "version", "python_version", "pytorch_version")
            if system.get(key) is not None
        },
    }


def runtime_profile_from(profile: dict[str, Any]) -> str:
    versions = profile.get("versions", {})
    version_text = ", ".join(
        f"{key}={value}" for key, value in versions.items()
    ) or "版本字段未提供"
    device_name = profile.get("device", {}).get("name", "未知设备")
    flags = " ".join(profile.get("verified_flags", []))
    return (
        f"memory_profile={profile.get('memory_profile', '未记录')}；"
        f"system_stats 已核验启动参数 {flags}；设备 {device_name}；{version_text}。"
        "CPU VAE 与 VRAM 模式仅依据启动参数记录；CLIP 编码器实际设备未由 system_stats "
        "证明，需从 ComfyUI 服务日志确认。"
    )


def check_queue_idle(base_url: str) -> None:
    status, queue, text = api_request(base_url, "/queue", timeout=15)
    if status != 200 or not isinstance(queue, dict):
        raise RunnerError(f"ComfyUI /queue GET 失败（HTTP {status}）：{text[:500]}")
    running = queue.get("queue_running")
    pending = queue.get("queue_pending")
    if not isinstance(running, list) or not isinstance(pending, list):
        raise RunnerError("ComfyUI /queue 响应缺少 queue_running/queue_pending；拒绝提交。")
    if running or pending:
        raise RunnerError(
            f"ComfyUI 当前非空闲（running={len(running)}, pending={len(pending)}）；拒绝提交。"
        )


def output_file(item: dict[str, Any]) -> Path:
    filename = item.get("filename")
    if not isinstance(filename, str) or not filename:
        raise RunnerError("ComfyUI history image entry 缺少 filename。")
    image_type = item.get("type", "output")
    subfolder = item.get("subfolder", "")
    if not isinstance(image_type, str) or not isinstance(subfolder, str):
        raise RunnerError("ComfyUI history image path 字段类型无效。")
    root = (PROJECT_ROOT / "ComfyUI").resolve()
    path = (root / image_type / subfolder / filename).resolve()
    if not path.is_relative_to(root):
        raise RunnerError("ComfyUI history image path 越出 ComfyUI 目录。")
    return path


def extract_history_record(body: Any, prompt_id: str) -> dict[str, Any] | None:
    if isinstance(body, dict) and isinstance(body.get(prompt_id), dict):
        return body[prompt_id]
    return None


def collect_history_images(history: dict[str, Any], case: dict[str, Any],
                           prompt_field: str) -> tuple[list[str], list[dict[str, Any]], list[str]]:
    paths: list[str] = []
    metadata: list[dict[str, Any]] = []
    errors: list[str] = []
    outputs = history.get("outputs", {})
    if not isinstance(outputs, dict):
        return paths, metadata, ["history.outputs 不是对象。"]
    for node_id, output in outputs.items():
        if not isinstance(output, dict):
            continue
        for item in output.get("images", []):
            if not isinstance(item, dict):
                continue
            try:
                path = output_file(item)
            except RunnerError as error:
                errors.append(str(error))
                continue
            paths.append(str(path))
            if path.is_file():
                info = inspect_image(
                    path, case.get("prompt_node"), prompt_field, case["prompt"]
                )
                info["output_node_id"] = str(node_id)
                info["filename"] = item.get("filename")
                metadata.append(info)
                if info.get("inspection_error"):
                    errors.append(f"输出图片无法解析：{path}: {info['inspection_error']}")
                if info.get("png_prompt_binding", {}).get("status") != "matched":
                    errors.append(f"PNG 提示词绑定未匹配：{path}")
                expected_size = [case.get("width"), case.get("height")]
                if all(isinstance(value, int) for value in expected_size) and info.get("dimensions") != expected_size:
                    errors.append(f"输出尺寸不符：{path}: {info.get('dimensions')} vs {expected_size}")
            else:
                errors.append(f"history 引用的输出文件不存在：{path}")
                metadata.append({"path": str(path), "output_node_id": str(node_id),
                                 "inspection_error": "文件不存在"})
    return paths, metadata, errors


def terminal_history(history: dict[str, Any]) -> bool:
    status = history.get("status")
    return isinstance(status, dict) and str(status.get("status_str", "")).lower() in TERMINAL_STATUSES


def resource_sample(base_url: str, elapsed: float) -> dict[str, Any]:
    memory = psutil.virtual_memory()
    sample = {"elapsed_seconds": round(elapsed, 2), "host_ram_used_bytes": memory.total-memory.available,
              "host_ram_available_bytes": memory.available}
    try:
        code, stats, _ = api_request(base_url, "/system_stats", timeout=3)
        if code == 200 and isinstance(stats, dict):
            sample["devices"] = stats.get("devices", [])
    except (TimeoutError, urllib.error.URLError, OSError):
        sample["device_sample_unavailable"] = True
    return sample


def run_case(case: dict[str, Any], graph: dict[str, Any], base_url: str,
             preflight: dict[str, Any], probe: dict[str, Any], timeout: int,
             poll_seconds: float) -> None:
    case_id = safe_case_id(case.get("id"))
    folder = HERE / "cases" / case_id
    result_path = folder / "result.json"
    submission_path = folder / "submission.json"
    history_path = folder / "history.json"
    if result_path.exists():
        print(f"SKIP existing result: {case_id}", flush=True)
        return
    if submission_path.exists() or history_path.exists():
        raise RunnerError(
            f"{case_id}: 有 submission/history 但无 result.json；为防止重复提交，先人工核对证据。"
        )

    folder.mkdir(parents=True, exist_ok=True)
    write_json(folder / "api.json", graph)
    started_at = datetime.now(timezone.utc).isoformat()
    start = time.monotonic()
    submission = {
        "submitted_at": started_at,
        "state": "request_started_outcome_unknown",
        "prompt_graph_sha256": hashlib.sha256(
            json.dumps(graph, ensure_ascii=False, sort_keys=True).encode("utf-8")
        ).hexdigest(),
    }
    write_json(submission_path, submission)
    try:
        http_status, response, raw = api_request(
            base_url, "/prompt", method="POST", body={"prompt": graph}, timeout=60
        )
    except (TimeoutError, urllib.error.URLError, OSError) as error:
        submission["request_error"] = str(error)
        write_json(submission_path, submission)
        raise RunnerError(
            f"{case_id}: POST 结果不确定，已保留提交保护记录；先人工核对队列/历史再恢复。"
        ) from error
    submission.update(
        state="response_received",
        http_status=http_status,
        response=response if response is not None else raw,
    )
    write_json(submission_path, submission)
    if http_status != 200 or not isinstance(response, dict) or not response.get("prompt_id"):
        raise RunnerError(f"{case_id}: ComfyUI 未返回 prompt_id；已保存 submission.json，未生成 result.json。")

    prompt_id = str(response["prompt_id"])
    submission.update(state="accepted", prompt_id=prompt_id)
    write_json(submission_path, submission)
    print(f"SUBMITTED {case_id} prompt_id={prompt_id}", flush=True)

    deadline = time.monotonic() + timeout
    history: dict[str, Any] | None = None
    resources: list[dict[str, Any]] = []
    while time.monotonic() < deadline:
        resources.append(resource_sample(base_url, time.monotonic()-start))
        write_json(folder / "resource-samples.json", resources)
        try:
            history_status, history_body, history_text = api_request(
                base_url, "/history/" + urllib.parse.quote(prompt_id, safe=""), timeout=45
            )
            candidate = extract_history_record(history_body, prompt_id) if history_status == 200 else None
            if candidate and terminal_history(candidate):
                history = candidate
                write_json(history_path, history)
                break
            if history_status not in (200, 404):
                print(f"POLL {case_id}: HTTP {history_status} {history_text[:160]}", flush=True)
        except (TimeoutError, urllib.error.URLError) as error:
            print(f"POLL {case_id}: {error}", flush=True)
        time.sleep(poll_seconds)

    if history is None:
        raise RunnerError(
            f"{case_id}: 等待 {timeout}s 仍无终态 history；已保留 submission.json，未生成 result.json。"
        )

    api_status = str(history.get("status", {}).get("status_str", "unknown"))
    prompt_inputs = graph[str(case["prompt_node"])]["inputs"]
    prompt_field = "text" if "text" in prompt_inputs else "prompt"
    images, image_metadata, image_errors = collect_history_images(history, case, prompt_field)
    execution_errors = []
    status_messages = history.get("status", {}).get("messages", [])
    if isinstance(status_messages, list):
        execution_errors = [
            message[1] for message in status_messages
            if isinstance(message, (list, tuple)) and len(message) == 2
            and message[0] == "execution_error"
        ]
    planned_runtime_profile = case.get(
        "planned_runtime_profile", case.get("runtime_profile")
    )
    result = {
        **case,
        "planned_runtime_profile": planned_runtime_profile,
        "runtime_profile": preflight["runtime_profile"],
        "memory_profile": preflight["memory_profile"],
        "status": api_status,
        "prompt_id": prompt_id,
        "started_at": started_at,
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "elapsed_seconds": round(time.monotonic() - start, 2),
        "preflight": {"gpu_probe": probe, **preflight},
        "system_stats": preflight["system_stats"],
        "images": images,
        "image_metadata": image_metadata,
        "output_validation_status": "failed" if image_errors else "passed" if images else "no_images",
        "visual_review": "pending",
        "resource_samples": str(folder / "resource-samples.json"),
        "observed_peak_host_ram_used_bytes": max((s["host_ram_used_bytes"] for s in resources), default=None),
        "observed_peak_vram_used_bytes": max((d["vram_total"]-d["vram_free"] for s in resources for d in s.get("devices", []) if "vram_total" in d and "vram_free" in d), default=None),
        "resource_sampling_limit": "周期采样得到的已观测最大值，非精确峰值；host RAM包含系统及其他进程。",
        "errors": execution_errors + image_errors,
    }
    write_json(result_path, result)
    print(
        f"DONE {case_id} status={api_status} images={len(images)} "
        f"elapsed_seconds={result['elapsed_seconds']}",
        flush=True,
    )
    if api_status != "success" or not images:
        raise RunnerError(f"{case_id}: 实际 history 记录为 {api_status}，或没有输出图片；已保留结果证据。")
    if image_errors:
        raise RunnerError(f"{case_id}: API 已结束，但输出完整性或 PNG 提示词绑定检查失败；已保留证据，停止后续案例。")


def load_cases() -> list[dict[str, Any]]:
    path = HERE / "cases.json"
    try:
        cases = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as error:
        raise RunnerError(f"无法读取 cases.json：{error}") from error
    if not isinstance(cases, list):
        raise RunnerError("cases.json 顶层必须是数组。")
    seen: set[str] = set()
    for case in cases:
        if not isinstance(case, dict):
            raise RunnerError("cases.json 每项必须是对象。")
        case_id = safe_case_id(case.get("id"))
        if case_id in seen:
            raise RunnerError(f"cases.json 中 id 重复：{case_id}")
        seen.add(case_id)
    return cases


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--case", action="append",
        help="只运行一个 cases.json 中的 id；pending cases 混用 memory_profile 时必须指定",
    )
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--timeout", type=int, default=DEFAULT_RUN_TIMEOUT)
    parser.add_argument("--poll-seconds", type=float, default=5.0)
    parser.add_argument(
        "--prepare-only",
        action="store_true",
        help="只生成 prepared/<id>.api.json 与未提交标记；不调用服务或触碰 cases/<id>。",
    )
    args = parser.parse_args()
    if args.timeout <= 0 or args.poll_seconds <= 0:
        parser.error("--timeout 和 --poll-seconds 必须为正数")

    cases = load_cases()
    if args.case:
        requested=set(args.case)
        missing=requested-{case.get('id') for case in cases}
        if missing:
            raise RunnerError(f"cases.json 中找不到 case：{sorted(missing)}")
        cases = [case for case in cases if case.get("id") in requested]

    if args.prepare_only:
        prepared_dir = HERE / "prepared"
        prepared_dir.mkdir(parents=True, exist_ok=True)
        for case in cases:
            case_id = safe_case_id(case["id"])
            graph_path = prepared_dir / f"{case_id}.api.json"
            manifest_path = prepared_dir / f"{case_id}.json"
            write_json(graph_path, build_graph(case))
            write_json(
                manifest_path,
                {
                    "id": case_id,
                    "status": "prepared_not_submitted",
                    "submitted": False,
                    "prepared_at": datetime.now(timezone.utc).isoformat(),
                    "api_file": str(graph_path),
                    "planned_runtime_profile": case.get(
                        "planned_runtime_profile", case.get("runtime_profile")
                    ),
                },
            )
            print(f"PREPARED only; no submission: {case_id}", flush=True)
        return 0

    pending: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for case in cases:
        folder = HERE / "cases" / safe_case_id(case["id"])
        if (folder / "result.json").exists():
            print(f"SKIP existing result: {case['id']}", flush=True)
            continue
        if (folder / "submission.json").exists() or (folder / "history.json").exists():
            raise RunnerError(
                f"{case['id']}: 有 submission/history 但无 result.json；防重复提交已停止。"
            )
        pending.append((case, build_graph(case)))

    if not pending:
        print("没有待运行的案例。", flush=True)
        return 0

    pending_profiles = set()
    for case, _ in pending:
        profile = case.get("memory_profile", "legacy-lowvram")
        if not isinstance(profile, str):
            raise RunnerError(f"{case['id']}: memory_profile 必须是字符串。")
        if profile not in MEMORY_PROFILES:
            raise RunnerError(f"{case['id']}: 不支持的 memory_profile：{profile!r}")
        pending_profiles.add(profile)
    if len(pending_profiles) > 1:
        raise RunnerError(
            "pending cases 混用了 memory_profile："
            + ", ".join(sorted(pending_profiles))
            + "；请通过 --case 每次选择单一 profile 的案例。"
        )
    memory_profile = next(iter(pending_profiles))
    print(f"MEMORY_PROFILE {memory_profile}", flush=True)

    # The local health gate is checked before any API POST. Failed, stale, or
    # incomplete latest probes stop the run without fabricating a result file.
    probe = require_fresh_healthy_probe()
    preflight = check_api_preflight(args.base_url, pending, memory_profile)
    for case, graph in pending:
        check_queue_idle(args.base_url)
        run_case(case, graph, args.base_url, preflight, probe, args.timeout, args.poll_seconds)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RunnerError as error:
        raise SystemExit(str(error))
