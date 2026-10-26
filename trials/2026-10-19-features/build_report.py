"""Build a small offline HTML and Markdown report for the feature trials.

Run with:
    python trials/2026-10-19-features/build_report.py

Only Python's standard library is used. Missing result and asset files are
handled without creating broken image links.
"""

from __future__ import annotations

import html
import json
import os
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import quote


HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parents[1]
COMFY = PROJECT_ROOT / "ComfyUI"
COMFY_INPUT = COMFY / "input"
COMFY_OUTPUT = COMFY / "output"
ALLOWED_ASSET_ROOTS = (HERE, PROJECT_ROOT / "trials", COMFY_INPUT, COMFY_OUTPUT)


def read_json(path: Path, fallback):
    """Read JSON, returning fallback for a missing or malformed file."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return fallback


def text(value, fallback="未提供") -> str:
    if value is None or value == "":
        return fallback
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, indent=2)
    return str(value)


def safe_asset(path: Path) -> Path | None:
    """Return an existing file only when it is inside a report asset root."""
    try:
        resolved = path.resolve(strict=True)
        if not resolved.is_file():
            return None
        for root in ALLOWED_ASSET_ROOTS:
            try:
                resolved.relative_to(root.resolve())
                return resolved
            except (OSError, ValueError):
                continue
    except OSError:
        return None
    return None


def input_asset(reference: str) -> Path | None:
    """Resolve a case input name or a ComfyUI/input-relative reference."""
    value = str(reference).strip().replace("\\", "/")
    if not value:
        return None

    raw_path = Path(value)
    candidates: list[Path] = []
    if raw_path.is_absolute():
        candidates.append(raw_path)
    else:
        normalized = value.lstrip("/")
        if normalized.startswith("featurebench/"):
            candidates.append(COMFY_INPUT / Path(normalized))
        else:
            candidates.append(COMFY_INPUT / Path(normalized))
            if "/" not in normalized:
                filename = normalized if Path(normalized).suffix else normalized + ".png"
                candidates.append(COMFY_INPUT / "featurebench" / filename)
            candidates.extend((HERE / Path(normalized), PROJECT_ROOT / Path(normalized)))

    for candidate in candidates:
        resolved = safe_asset(candidate)
        if resolved is not None:
            return resolved
    return None


def result_asset(image) -> Path | None:
    """Resolve a result image path or a ComfyUI history image record."""
    candidates: list[Path] = []
    if isinstance(image, dict):
        raw_path = image.get("path") or image.get("image")
        filename = image.get("filename")
        subfolder = image.get("subfolder", "")
        image_type = image.get("type", "output")
        if raw_path:
            return result_asset(raw_path)
        if filename:
            base = COMFY_INPUT if image_type == "input" else COMFY_OUTPUT
            candidates.append(base / str(subfolder) / str(filename))
            candidates.append(base / str(filename))
    elif image is not None:
        raw = re.sub(r"/+", "/", str(image).strip().replace("\\", "/"))
        if raw:
            # Historical Windows records bind to the same public subtree on Linux.
            match = re.search(r"(?:^|/)ComfyUI/(input|output)/(.+)$", raw, re.IGNORECASE)
            if match and ".." not in Path(match.group(2)).parts:
                base = COMFY_INPUT if match.group(1).lower() == "input" else COMFY_OUTPUT
                candidates.append(base / match.group(2))
            raw_path = Path(raw)
            if raw_path.is_absolute():
                candidates.append(raw_path)
            else:
                candidates.extend(
                    (
                        HERE / raw_path,
                        PROJECT_ROOT / raw_path,
                        COMFY_OUTPUT / raw_path,
                        COMFY_INPUT / raw_path,
                        COMFY_OUTPUT / raw_path.name,
                    )
                )

    for candidate in candidates:
        resolved = safe_asset(candidate)
        if resolved is not None:
            return resolved
    return None


def image_items(value) -> list:
    if isinstance(value, list):
        return value
    if value is None or value == "":
        return []
    return [value]


def image_url(path: Path) -> str:
    relative = os.path.relpath(path, HERE).replace(os.sep, "/")
    return quote(relative, safe="/:@._~-()")


def case_inputs(case: dict) -> list[dict]:
    """Build numbered input entries, deduplicating aliases to the same file."""
    entries: list[dict] = []
    seen: set[Path] = set()

    for index, name in enumerate(image_items(case.get("inputs")), start=1):
        label = str(name)
        path = input_asset(label)
        if path is not None:
            seen.add(path)
        entries.append({"label": f"输入 {index} · {label}", "path": path})

    for reference in image_items(case.get("refs")):
        path = input_asset(str(reference))
        if path is None or path in seen:
            continue
        seen.add(path)
        entries.append({"label": f"输入 {len(entries) + 1} · {Path(str(reference)).name}", "path": path})

    return entries


def split_outputs(images: list, inpaint: bool) -> tuple[list[Path], list[Path]]:
    resolved = [path for item in images if (path := result_asset(item)) is not None]
    if not inpaint:
        return resolved, []

    outputs: list[Path] = []
    attachments: list[Path] = []
    for path in resolved:
        stem = path.stem.lower()
        if re.search(r"(?:^|[-_])(?:mask|input)(?:[-_.]|$)", stem):
            attachments.append(path)
        else:
            outputs.append(path)
    return outputs[:1], attachments


def review_for(case_id: str, reviews, record: dict | None):
    review = reviews.get(case_id) if isinstance(reviews, dict) else None
    if review is None and isinstance(record, dict):
        review = record.get("review")
    if review in (None, "", "pending", "待评估"):
        return "尚未进行视觉检查", ""
    if isinstance(review, dict):
        verdict = review.get("verdict") or review.get("status") or "已记录视觉结论"
        detail = review.get("detail") or review.get("notes") or ""
        return text(verdict), text(detail, "")
    return text(review), ""


def elapsed_value(record: dict | None):
    if not isinstance(record, dict):
        return None
    value = record.get("elapsed_seconds", record.get("elapsed"))
    if value is None and record.get("batch_elapsed_seconds") is not None:
        return f"整个批次 {float(record['batch_elapsed_seconds']):g} 秒（非单项耗时）"
    if value is None:
        return None
    try:
        return f"{float(value):g} 秒"
    except (TypeError, ValueError):
        return str(value)


def runtime_profile_value(case: dict) -> str:
    value = case.get("runtime_profile")
    return "" if value is None or value == "" else text(value, "")


def mask_measurement_lines(audit_record: dict | None) -> list[str]:
    if not isinstance(audit_record, dict):
        return []
    measurement = audit_record.get("mask_measurement")
    if not isinstance(measurement, dict):
        return []

    def count(value) -> str:
        if value is None:
            return "未记录"
        try:
            return f"{int(value):,}"
        except (TypeError, ValueError):
            return text(value)

    return [
        "按 8 位遮罩 PNG 统计，遮罩外改变像素 / 总像素："
        f"{count(measurement.get('outside_changed_pixels'))} / "
        f"{count(measurement.get('outside_pixels'))}",
        "遮罩内改变像素 / 总像素："
        f"{count(measurement.get('inside_changed_pixels'))} / "
        f"{count(measurement.get('inside_pixels'))}",
        "遮罩外像素保留由最终合成节点实现，不归因于模型本身。",
        "极小的正羽化值可能在遮罩 PNG 中量化为 0；需结合浮点遮罩支持范围判断边缘差异。",
    ]


def record_status(record: dict | None, exists: bool, output_count: int, blocked=False) -> str:
    if blocked:
        return "阻塞 · 无输出"
    if not exists:
        return "尚无已收集的执行结果"
    if not isinstance(record, dict):
        return "结果文件无法读取 · 无输出"
    status = str(record.get("status", "")).strip()
    if status.lower() == "partial_output":
        return "批次崩溃后恢复图片（非全批成功）"
    if status.lower() in ("success", "completed", "complete"):
        return "API 执行成功" if output_count else "API 执行成功 · 无可用输出图片"
    if not status:
        return "历史记录" if output_count else "无输出"
    return f"失败（{status}）" if not output_count else f"未完整执行（{status}）"


def source_level(case: dict) -> str:
    return text(case.get("claim_level") or case.get("source_level") or case.get("source"))


def display_model(case: dict) -> str:
    model = text(case.get("model"), "未知")
    lower = model.lower()
    # Z-Image names also contain "Turbo" and the GGUF encoder name contains
    # "Qwen". Preserve the case's actual model label before legacy Qwen aliases.
    if "z-image" in lower or "zimage" in lower:
        return model
    if "moss" in lower:
        return "MOSS-Image-5B"
    if "kroma" in lower:
        return "Kroma v0.3.1 OPD Q2"
    if "turbo-plain" in str(case.get("id", "")) or "普通 Turbo 对照" in model:
        return "Qwen 2.1 Turbo（普通对照）"
    if "turbo-un" in lower or "uncensored" in lower or "turbo-un" in str(case.get("id", "")):
        return "Qwen 2.1 Turbo-UN"
    if "turbo" in lower:
        return "Qwen 2.1 Turbo（普通对照）"
    if "qwen" in lower:
        return "Qwen-Image-2.1"
    return model


def setup_note(case: dict) -> str:
    notes = []
    if case.get("model") == "kroma" and case.get("recipe") == "reference":
        ref_size = case.get("reference_vae_resolution", 1024)
        notes.append(f"输出 512×512；参考 VAE 编码 {ref_size}×{ref_size}，视觉编码约 384×384；当前 Q2 未加载专用风格或 BFS LoRA。")
    if case.get("retry_reason"):
        notes.append(str(case["retry_reason"]))
    return " ".join(notes)


def model_key(case: dict) -> str:
    return display_model(case).lower()


def workflow_path(case_id: str) -> Path | None:
    return safe_asset(HERE / "cases" / case_id / "api.json")


def legacy_api_path(case: dict) -> Path | None:
    """Find a recorded *api.json workflow inside this workspace."""
    trials_root = PROJECT_ROOT

    def strings(value):
        if isinstance(value, str):
            yield value
        elif isinstance(value, dict):
            for child in value.values():
                yield from strings(child)
        elif isinstance(value, list):
            for child in value:
                yield from strings(child)

    def allowed(path: Path) -> Path | None:
        try:
            resolved = path.resolve(strict=True)
            resolved.relative_to(trials_root.resolve())
            if resolved.is_file() and resolved.name.lower().endswith("api.json"):
                return resolved
        except (OSError, ValueError):
            return None
        return None

    for field in ("api_json", "workflow", "evidence"):
        value = case.get(field)
        for raw in strings(value):
            raw = raw.strip()
            tokens = re.findall(r'''[^\s"'<>|,;]+api\.json''', raw, flags=re.IGNORECASE)
            if raw.lower().endswith("api.json"):
                tokens.insert(0, raw)
            for token in tokens:
                token = token.strip("()[]{}")
                token = token.replace("file://", "")
                drive_match = re.search(r"[A-Za-z]:[\\/]", token)
                trials_match = re.search(r"trials[\\/]", token, flags=re.IGNORECASE)
                if drive_match:
                    token = token[drive_match.start():]
                elif trials_match:
                    token = token[trials_match.start():]

                raw_path = Path(token.replace("/", os.sep))
                candidates = [raw_path] if raw_path.is_absolute() else [
                    HERE / raw_path,
                    PROJECT_ROOT / raw_path,
                    trials_root / raw_path,
                ]
                for candidate in candidates:
                    resolved = allowed(candidate)
                    if resolved is not None:
                        return resolved
    return None


def case_workflow_path(case: dict, case_id: str, baseline: bool) -> Path | None:
    if baseline:
        return legacy_api_path(case)
    return workflow_path(case_id)


def directory_item(case: dict, reviews, record: dict | None, anchor_id: str,
                   *, blocked=False) -> str:
    case_id = text(case.get("id"), "未命名")
    verdict, _ = review_for(case_id, reviews, record)
    if blocked:
        verdict = "未执行（阻塞）"
    return (
        f'<li class="directory-item" data-model="{html.escape(model_key(case), quote=True)}">'
        f'<a href="#{quote(anchor_id, safe="-._~")}">'
        f'<span class="directory-model">{html.escape(display_model(case))}</span>'
        f'<span class="directory-feature">{html.escape(text(case.get("feature"), case_id))}</span>'
        f'<span class="directory-verdict">{html.escape(verdict)}</span>'
        "</a></li>"
    )


def html_image(path: Path, label: str, class_name="") -> str:
    cls = f' class="{html.escape(class_name, quote=True)}"' if class_name else ""
    url = html.escape(image_url(path), quote=True)
    return (
        f'<figure{cls}><a class="image-open" href="{url}" target="_blank" rel="noopener" '
        f'title="在新标签页打开原图"><img src="{url}" '
        f'alt="{html.escape(label, quote=True)}" loading="lazy"></a>'
        f"<figcaption>{html.escape(label)}</figcaption></figure>"
    )


def html_input_panel(inputs: list[dict]) -> str:
    if not inputs:
        return '<p class="muted">此功能没有输入图片。</p>'
    rendered = []
    for item in inputs:
        path = item["path"]
        if path is None:
            rendered.append(
                f'<div class="missing">{html.escape(item["label"])}<br>输入图片未找到</div>'
            )
        else:
            rendered.append(html_image(path, item["label"]))
    return '<div class="image-list">' + "".join(rendered) + "</div>"


def html_output_panel(outputs: list[Path], attachments: list[Path], not_run: bool) -> str:
    if outputs:
        rendered = '<div class="image-list">' + "".join(
            html_image(path, f"输出 {index}") for index, path in enumerate(outputs, start=1)
        ) + "</div>"
    else:
        message = "尚无已收集的输出" if not_run else "无输出"
        rendered = f'<div class="missing output-empty">{message}</div>'
    if attachments:
        rendered += '<details class="attachments"><summary>附件（遮罩／输入等）</summary>'
        rendered += '<div class="image-list">' + "".join(
            html_image(path, f"附件 {index} · {path.name}")
            for index, path in enumerate(attachments, start=1)
        ) + "</div></details>"
    return rendered


def render_case_html(case: dict, reviews, record: dict | None, result_exists: bool,
                     audit_record: dict | None = None,
                     *, blocked=False, baseline=False, anchor_id=None) -> str:
    case_id = text(case.get("id"), "未命名")
    anchor_id = anchor_id or case_id
    review, review_detail = review_for(case_id, reviews, record)
    inpaint = case.get("recipe") == "inpaint" or case_id == "qwen-inpaint" or bool(case.get("mask_attachments"))
    output_images = image_items(record.get("images")) if isinstance(record, dict) else []
    outputs, attachments = split_outputs(output_images, inpaint)
    if blocked:
        outputs, attachments = [], []
    elapsed = elapsed_value(record)
    status = record_status(record, result_exists, len(outputs), blocked=blocked)
    if baseline and not outputs and result_exists:
        status = "历史记录 · 无可用输出图片"
    inputs = case_inputs(case)

    props = [
        ("模型", display_model(case)),
        ("功能", text(case.get("feature"))),
        ("来源级别", source_level(case)),
    ]
    metadata = "".join(
        f'<div><span>{html.escape(label)}</span><strong>{html.escape(value)}</strong></div>'
        for label, value in props
    )
    if blocked:
        review, review_detail = review_for(case_id, reviews, case)
        if not review_detail:
            review_detail = text(case.get("reason"), "未提供阻塞原因。")
        evidence = text(case.get("evidence"), "未提供证据。")
        review_detail += f"\n证据：{evidence}"

    workflow = case_workflow_path(case, case_id, baseline) if not blocked else None
    workflow_label = "查看旧基线 workflow / api.json" if baseline else "查看 workflow / api.json"
    workflow_html = (
        f'<a href="{html.escape(image_url(workflow), quote=True)}">{workflow_label}</a>'
        if workflow else '<span class="muted">暂无 api.json</span>'
    )
    if case.get("prior_attempt_evidence"):
        previous = safe_asset(HERE / case["prior_attempt_evidence"])
        if previous:
            workflow_html += f' · <a href="{html.escape(image_url(previous), quote=True)}">先前失败记录</a>'
    prompt = text(case.get("prompt"), "未提供")
    if case.get("recipe") == "caption":
        generated = record.get("text_outputs", []) if isinstance(record, dict) else []
        prompt = "自动反推的实际提示词：\n" + ("\n".join(str(item) for item in generated) if generated else "尚无反推文本；见任务记录。")
    expected = text(case.get("expected"), "未提供")
    details_html = (
        '<details class="prompt"><summary>展开 Prompt、预期结果与 workflow</summary>'
        f'<p>{html.escape(setup_note(case))}</p>'
        f'<h4>Prompt</h4><pre>{html.escape(prompt)}</pre>'
        f'<h4>预期结果</h4><p>{html.escape(expected)}</p>'
        f'<p>{workflow_html}</p></details>'
    )
    if blocked:
        details_html = (
            '<details class="prompt"><summary>展开阻塞原因与证据</summary>'
            f'<p>{html.escape(text(case.get("reason")))}</p>'
            f'<pre>{html.escape(text(case.get("evidence")))}</pre></details>'
        )

    elapsed_html = f'<span class="elapsed">耗时：{html.escape(elapsed)}</span>' if elapsed else ""
    runtime_profile = runtime_profile_value(case)
    runtime_html = (
        f'<div class="runtime-profile"><strong>运行配置：</strong>'
        f'{html.escape(runtime_profile)}</div>'
        if runtime_profile else ""
    )
    mask_lines = mask_measurement_lines(audit_record) if inpaint else []
    mask_html = (
        '<aside class="audit-note"><strong>遮罩像素核验</strong>'
        + "".join(f"<p>{html.escape(line)}</p>" for line in mask_lines)
        + "</aside>"
        if mask_lines else ""
    )
    result_label = "历史输出" if baseline else "执行输出"
    output_panel = html_output_panel(outputs, attachments, not_run=not result_exists and not blocked)
    animation = result_asset(record.get("animation")) if isinstance(record, dict) else None
    if animation and not blocked:
        output_panel += f'<p><a href="{html.escape(image_url(animation), quote=True)}">查看原始 WebP 动画（5帧诊断，约0.2秒）</a></p>'
    input_heading = "输入图片"
    input_panel = html_input_panel(inputs)
    if not inputs and not blocked:
        input_heading = "文字输入"
        input_panel = f'<pre class="text-input">{html.escape(prompt)}</pre>'
    if blocked:
        output_panel = '<div class="missing output-empty">无输出</div>'
    return (
        f'<article class="case-card" id="{html.escape(anchor_id, quote=True)}" '
        f'data-model="{html.escape(model_key(case), quote=True)}">'
        f'<div class="card-heading"><div><p class="eyebrow">'
        f'{"旧有文生图基线" if baseline else "阻塞项" if blocked else "功能试验"}</p>'
        f'<h2>{html.escape(text(case.get("feature"), case_id))}</h2>'
        f'<code>{html.escape(case_id)}</code></div>'
        f'<span class="status">{html.escape(status)}</span></div>'
        f'<div class="metadata">{metadata}</div>'
        f'<div class="review"><strong>视觉结论：{html.escape(review)}</strong>'
        f'{f"<p>{html.escape(review_detail)}</p>" if review_detail else ""}</div>'
        f'{runtime_html}{mask_html}'
        f'<div class="timing">{elapsed_html}</div>'
        f'<div class="media-grid"><section><h3>{input_heading}</h3>{input_panel}</section>'
        f'<section><h3>{result_label}</h3>{output_panel}</section></div>'
        f'{details_html}</article>'
    )


def md_image(path: Path, label: str) -> str:
    relative = image_url(path)
    return f"![{label}]({relative})"


def markdown_case(case: dict, reviews, record: dict | None, result_exists: bool,
                  audit_record: dict | None = None,
                  *, blocked=False, baseline=False) -> str:
    case_id = text(case.get("id"), "未命名")
    review, review_detail = review_for(case_id, reviews, record)
    inpaint = case.get("recipe") == "inpaint" or case_id == "qwen-inpaint" or bool(case.get("mask_attachments"))
    raw_images = image_items(record.get("images")) if isinstance(record, dict) else []
    outputs, attachments = split_outputs(raw_images, inpaint)
    if blocked:
        outputs, attachments = [], []
        review, review_detail = review_for(case_id, reviews, case)
        review_detail = f"{review_detail or text(case.get('reason'))}\n证据：{text(case.get('evidence'))}"
    status = record_status(record, result_exists, len(outputs), blocked=blocked)
    if baseline and not outputs and result_exists:
        status = "历史记录 · 无可用输出图片"
    elapsed = elapsed_value(record)
    heading = text(case.get("feature"), case_id)
    lines = [f"## {heading}（`{case_id}`）", "",
             f"- 模型：{display_model(case)}",
             f"- 来源级别：{source_level(case)}",
             f"- 执行：{status}" + (f"；耗时：{elapsed}" if elapsed else ""),
             f"- 视觉结论：{review}"]
    runtime_profile = runtime_profile_value(case)
    if runtime_profile:
        lines.append(f"- 运行配置：{runtime_profile}")
    mask_lines = mask_measurement_lines(audit_record) if inpaint else []
    if mask_lines:
        lines.extend(("", "遮罩像素核验：", *(f"- {line}" for line in mask_lines)))
    if review_detail:
        lines.extend(("", review_detail))
    if setup_note(case):
        lines.extend(("", setup_note(case)))
    lines.extend(("", "输入图片："))
    inputs = case_inputs(case)
    if inputs:
        for item in inputs:
            if item["path"] is None:
                lines.append(f"- {item['label']}：输入图片未找到")
            else:
                lines.append(f"- {item['label']}：{md_image(item['path'], item['label'])}")
    else:
        lines.append("- 此功能没有输入图片。")
    lines.extend(("", "输出图片："))
    if outputs:
        lines.extend(md_image(path, f"输出 {index}") for index, path in enumerate(outputs, start=1))
    else:
        lines.append("- 尚无已收集的输出" if not result_exists and not blocked else "- 无输出")
    if attachments:
        lines.extend(("", "附件："))
        lines.extend(f"- {path.name}：{md_image(path, path.name)}" for path in attachments)
    animation = result_asset(record.get("animation")) if isinstance(record, dict) else None
    if animation and not blocked:
        lines.extend(("", f"[查看原始 WebP 动画（5帧诊断，约0.2秒）]({image_url(animation)})"))
    if blocked:
        lines.extend(("", f"阻塞原因：{text(case.get('reason'))}",
                      f"证据：{text(case.get('evidence'))}"))
    else:
        prompt_text = text(case.get("prompt"))
        if case.get("recipe") == "caption" and isinstance(record, dict):
            prompt_text = "自动反推的实际提示词：\n" + "\n".join(str(value) for value in record.get("text_outputs", []))
        lines.extend(("", "<details>", "<summary>Prompt、预期结果与 workflow</summary>", "",
                      "Prompt:", "", "```text", prompt_text, "```", "",
                      f"预期结果：{text(case.get('expected'))}", ""))
        workflow = case_workflow_path(case, case_id, baseline)
        if workflow:
            label = f"旧基线 api.json：{workflow.name}" if baseline else f"{case_id}/api.json"
            lines.append(f"workflow / api.json：[{label}]({image_url(workflow)})")
        else:
            lines.append("workflow / api.json：暂无")
        lines.extend(("", "</details>"))
    return "\n".join(lines)


def render_html(cards: list[str], directory: list[str], models: dict[str, str],
                case_count: int, blocked_count: int) -> str:
    generated = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %Z")
    options = "".join(
        f'<option value="{html.escape(key, quote=True)}">{html.escape(label)}</option>'
        for key, label in models.items()
    )
    directory_html = "".join(directory) or '<li class="muted">暂无卡片</li>'
    pending = read_json(PROJECT_ROOT / "research/pending-models.json", [])
    pending_html = ""
    if pending:
        entries = "".join(
            f'<p><a href="{html.escape(str(item.get("source_url", "")), quote=True)}">'
            f'{html.escape(item.get("title") or "新增微信文章：标题／模型待确认")}</a> · '
            f'{html.escape(item.get("model") or "模型名未知")} · 尚未执行'
            f'{"；来源已确认，整合包需登录下载，内部权重待核验" if item.get("status") == "pending_exact_weights" else ""}'
            + (f' · <a href="{html.escape(item["mirror_url"], quote=True)}">作者镜像页</a>' if item.get("mirror_url") else "")
            + (f' · <a href="{html.escape(item["download_url"], quote=True)}">下载来源</a>' if item.get("download_url") else "")
            + '</p>'
            for item in pending if str(item.get("status", "")).startswith("pending")
        )
        if entries:
            pending_html = '<section class="directory"><h2>新增待测清单</h2>' + entries + '<p class="muted">接在当前功能试验之后。未读取正文的条目不猜测模型与功能。</p></section>'
    return f'''<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ComfyUI 模型功能图像对照报告</title>
<style>
:root {{ color-scheme: light; --ink:#20302f; --muted:#667876; --line:#d9e2de; --paper:#f4f7f3; --card:#fff; --accent:#187a66; --soft:#e9f3ef; }}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:var(--paper); color:var(--ink); font:16px/1.55 "Segoe UI","Microsoft YaHei",sans-serif; }}
main {{ width:min(1180px, 100% - 32px); margin:32px auto 64px; }}
h1 {{ margin:0 0 8px; font-size:clamp(1.7rem,4vw,2.5rem); letter-spacing:-.03em; }}
.intro {{ padding:28px; border:1px solid var(--line); border-radius:20px; background:linear-gradient(135deg,#fff,#edf6f1); box-shadow:0 8px 30px #25463b0a; }}
.intro p {{ margin:8px 0; max-width:85ch; }}
.intro .scope {{ color:var(--muted); }}
.counts {{ display:flex; flex-wrap:wrap; gap:10px; margin-top:18px; }}
.counts span {{ background:var(--soft); border-radius:999px; padding:6px 12px; color:#28594f; font-size:.9rem; }}
.directory {{ margin-top:22px; padding:18px; border:1px solid var(--line); border-radius:16px; background:#fff; }}
.directory-heading {{ display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:12px; margin-bottom:12px; }}
.directory-heading h2 {{ margin:0; font-size:1.2rem; }}
.directory-filter {{ display:flex; align-items:center; gap:8px; color:var(--muted); font-size:.9rem; }}
.directory-filter select {{ max-width:240px; padding:7px 28px 7px 10px; border:1px solid var(--line); border-radius:8px; background:#fff; color:var(--ink); font:inherit; }}
.directory-list {{ display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:6px 10px; max-height:390px; overflow:auto; margin:0; padding:2px; list-style:none; }}
.directory-item {{ min-width:0; }}
.directory-item a {{ display:grid; grid-template-columns:100px minmax(0,1fr) minmax(125px,.9fr); align-items:center; gap:8px; min-height:42px; padding:7px 9px; border:1px solid #e8eeeb; border-radius:9px; background:#fbfcfb; color:var(--ink); text-decoration:none; font-size:.83rem; }}
.directory-item a:hover,.directory-item a:focus-visible {{ border-color:#83b4a7; background:var(--soft); outline:none; }}
.directory-model {{ color:var(--accent); font-weight:700; }}
.directory-feature,.directory-verdict {{ overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }}
.directory-verdict {{ color:var(--muted); }}
.directory-count {{ margin:6px 2px 0; color:var(--muted); font-size:.8rem; text-align:right; }}
.case-card {{ scroll-margin-top:18px; margin-top:22px; border:1px solid var(--line); border-radius:18px; background:var(--card); padding:22px; box-shadow:0 5px 24px #25463b08; }}
.case-card[hidden],.directory-item[hidden] {{ display:none !important; }}
.card-heading {{ display:flex; align-items:flex-start; justify-content:space-between; gap:18px; }}
.eyebrow {{ margin:0 0 4px; color:var(--accent); font-size:.76rem; font-weight:700; letter-spacing:.11em; text-transform:uppercase; }}
h2 {{ margin:0 0 4px; font-size:1.35rem; }}
code {{ color:var(--muted); font-size:.83rem; overflow-wrap:anywhere; }}
.status {{ flex:none; border-radius:999px; padding:6px 11px; background:var(--soft); color:#28594f; font-size:.86rem; font-weight:700; }}
.metadata {{ display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:10px; margin:18px 0; }}
.metadata div {{ min-width:0; padding:10px 12px; background:#f7f9f7; border-radius:10px; }}
.metadata span {{ display:block; margin-bottom:3px; color:var(--muted); font-size:.78rem; }}
.metadata strong {{ display:block; font-size:.94rem; overflow-wrap:anywhere; }}
.review {{ border-left:3px solid var(--accent); padding:2px 0 2px 13px; }}
.review p {{ margin:5px 0 0; color:#445754; white-space:pre-wrap; }}
.runtime-profile,.audit-note {{ margin-top:12px; padding:10px 12px; border-radius:10px; background:#f0f6f3; color:#445754; font-size:.9rem; white-space:pre-wrap; overflow-wrap:anywhere; }}
.runtime-profile strong,.audit-note strong {{ color:#28594f; }}
.audit-note p {{ margin:4px 0 0; }}
.timing {{ min-height:22px; color:var(--muted); font-size:.86rem; }}
.media-grid {{ display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:18px; margin-top:16px; }}
.media-grid section {{ min-width:0; padding:14px; border-radius:13px; background:#f8faf8; border:1px solid #e8eeeb; }}
h3 {{ margin:0 0 12px; font-size:1rem; }}
.image-list {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(min(100%,240px),1fr)); gap:12px; align-items:start; }}
figure {{ margin:0; min-width:0; padding:8px; border-radius:10px; background:#fff; border:1px solid var(--line); }}
figure .image-open {{ display:block; cursor:zoom-in; }}
figure img {{ display:block; width:100%; height:auto; max-height:50vh; object-fit:contain; }}
figcaption {{ padding:7px 2px 1px; color:var(--muted); font-size:.82rem; overflow-wrap:anywhere; }}
.missing {{ display:grid; place-items:center; min-height:120px; padding:18px; border:1px dashed #b9c8c2; border-radius:10px; color:var(--muted); text-align:center; background:#fbfcfb; }}
.output-empty {{ min-height:180px; font-size:1.05rem; font-weight:700; }}
.prompt,.attachments {{ margin-top:15px; border-top:1px solid var(--line); padding-top:12px; }}
summary {{ cursor:pointer; color:var(--accent); font-weight:700; }}
.prompt h4 {{ margin:14px 0 4px; }}
.prompt pre {{ max-height:330px; overflow:auto; padding:13px; border-radius:9px; background:#f4f7f5; white-space:pre-wrap; overflow-wrap:anywhere; font: .84rem/1.5 Consolas,monospace; }}
.prompt p {{ white-space:pre-wrap; }}
a {{ color:#126e5c; }}
.muted {{ color:var(--muted); }}
.text-input {{ margin:0; white-space:pre-wrap; overflow-wrap:anywhere; max-height:50vh; overflow:auto; font: .9rem/1.7 "Segoe UI","Microsoft YaHei",sans-serif; }}
footer {{ margin-top:30px; color:var(--muted); font-size:.84rem; }}
@media (max-width:760px) {{ main {{ width:min(100% - 20px,1180px); margin-top:10px; }} .intro,.case-card {{ padding:17px; border-radius:14px; }} .card-heading {{ flex-direction:column; gap:9px; }} .metadata {{ grid-template-columns:1fr; }} .media-grid {{ grid-template-columns:1fr; }} .directory-list {{ grid-template-columns:1fr; max-height:330px; }} .directory-item a {{ grid-template-columns:82px minmax(0,1fr); }} .directory-verdict {{ grid-column:2; }} }}
</style>
</head>
<body><main>
<header class="intro">
  <p class="eyebrow">离线试验报告</p>
  <h1>ComfyUI 模型功能图像对照</h1>
  <p>设备：RX 6650 XT（8 GB 显存）与 16 GB RAM。本轮 512 × 512；旧基线可为 768 × 768，以记录为准。</p>
  <p class="scope">来源边界：Z-Image 两篇用户提供的离线正文已核验，Flux.2 Klein 正文此前已正常读取；其他未读文章仍只依据可用索引、作者站外材料与上游证据。来源级别见每张卡片。</p>
  <p>精确节点参数请展开每张卡片并打开 workflow / api.json。API 执行成功只说明工作流成功返回；功能视觉成功以卡片中的视觉结论为准。</p>
  <div class="counts"><span>{case_count} 条功能／基线记录</span><span>{blocked_count} 条阻塞记录</span><span>生成于 {html.escape(generated)}</span></div>
</header>
{pending_html}
<nav class="directory" aria-label="试验卡片目录">
  <div class="directory-heading"><h2>卡片目录</h2>
    <label class="directory-filter" for="model-filter">模型筛选
      <select id="model-filter"><option value="">全部模型</option>{options}</select>
    </label>
  </div>
  <ul class="directory-list" id="case-index">{directory_html}</ul>
  <p class="directory-count" id="visible-count">{case_count + blocked_count} 项</p>
</nav>
{''.join(cards)}
<footer>点击图片可在新标签页查看本机原图。本页可直接离线打开。</footer>
</main>
<script>
(() => {{
  const selector = document.getElementById("model-filter");
  const cards = Array.from(document.querySelectorAll(".case-card"));
  const entries = Array.from(document.querySelectorAll(".directory-item"));
  const count = document.getElementById("visible-count");
  const update = () => {{
    const selected = selector.value;
    let visible = 0;
    for (const card of cards) {{
      const show = !selected || card.dataset.model === selected;
      card.hidden = !show;
      if (show) visible += 1;
    }}
    for (const entry of entries) {{
      entry.hidden = Boolean(selected) && entry.dataset.model !== selected;
    }}
    count.textContent = `${{visible}} / ${{cards.length}} 项`;
  }};
  selector.addEventListener("change", update);
}})();
</script>
</body></html>'''


def build_report() -> tuple[Path, Path]:
    cases = read_json(HERE / "cases.json", [])
    if not isinstance(cases, list):
        cases = []
    reviews = read_json(HERE / "reviews.json", {})
    if not isinstance(reviews, dict):
        reviews = {}
    blocked = read_json(HERE / "blocked.json", [])
    if not isinstance(blocked, list):
        blocked = []
    baseline = read_json(HERE / "baseline.json", [])
    if not isinstance(baseline, list):
        baseline = []
    audit_data = read_json(HERE / "output-audit.json", {})
    audit_items = audit_data.get("records", []) if isinstance(audit_data, dict) else []
    audit_records = {
        str(item.get("id")): item
        for item in audit_items
        if isinstance(item, dict) and item.get("id") is not None
    }

    html_cards: list[str] = []
    md_cards: list[str] = []
    directory: list[str] = []
    models: dict[str, str] = {}
    seen_anchors: set[str] = set()

    for case in cases:
        if not isinstance(case, dict):
            continue
        case_id = text(case.get("id"), "未命名")
        result_path = HERE / "cases" / case_id / "result.json"
        result_exists = result_path.is_file()
        record = read_json(result_path, None) if result_exists else None
        if not isinstance(record, dict):
            record = None
        audit_record = audit_records.get(case_id)
        html_cards.append(render_case_html(case, reviews, record, result_exists, audit_record))
        md_cards.append(markdown_case(case, reviews, record, result_exists, audit_record))
        directory.append(directory_item(case, reviews, record, case_id))
        models.setdefault(model_key(case), display_model(case))
        seen_anchors.add(case_id)

    for index, item in enumerate(baseline, start=1):
        if not isinstance(item, dict):
            continue
        case = dict(item)
        case_id = text(case.get("id"), f"baseline-{index}")
        case.setdefault("id", case_id)
        # Baseline entries carry their earlier output, timing, and review inline.
        record = {
            "images": case.get("images", []),
            "elapsed": case.get("elapsed", case.get("elapsed_seconds")),
            "review": case.get("review"),
            "status": case.get("status", "success"),
        }
        anchor = case_id
        if anchor in seen_anchors:
            anchor = f"{case_id}-baseline-{index}"
        seen_anchors.add(anchor)
        html_cards.append(render_case_html(case, {}, record, True, baseline=True, anchor_id=anchor))
        md_cards.append(markdown_case(case, {}, record, True, baseline=True))
        directory.append(directory_item(case, {}, record, anchor))
        models.setdefault(model_key(case), display_model(case))

    for index, item in enumerate(blocked, start=1):
        if not isinstance(item, dict):
            continue
        case = dict(item)
        case_id = text(case.get("id"), f"blocked-{index}")
        case.setdefault("id", case_id)
        anchor = case_id
        if anchor in seen_anchors:
            anchor = f"{case_id}-blocked-{index}"
        seen_anchors.add(anchor)
        html_cards.append(render_case_html(case, reviews, None, False, blocked=True, anchor_id=anchor))
        md_cards.append(markdown_case(case, reviews, None, False, blocked=True))
        directory.append(directory_item(case, reviews, None, anchor, blocked=True))
        models.setdefault(model_key(case), display_model(case))

    total = sum(1 for item in cases + baseline if isinstance(item, dict))
    html_path = HERE / "feature-report.html"
    markdown_path = HERE / "feature-report.md"
    html_path.write_text(
        render_html(html_cards, directory, models, total,
                    len([x for x in blocked if isinstance(x, dict)])),
        encoding="utf-8",
    )

    markdown = [
        "# ComfyUI 模型功能图像对照",
        "",
        "设备：RX 6650 XT（8 GB 显存）与 16 GB RAM。本轮 512 × 512；旧基线可为 768 × 768，以记录为准。",
        "",
        "来源边界：Z-Image 两篇用户提供的离线正文已核验，Flux.2 Klein 正文此前已正常读取；其他未读文章仍只依据可用索引、作者站外材料与上游证据。来源级别见每张卡片。",
        "",
        "精确节点参数见各卡片的 workflow / api.json。API 执行成功只说明工作流成功返回；功能视觉成功以视觉结论为准。",
        "",
        f"生成于：{datetime.now().astimezone().strftime('%Y-%m-%d %H:%M %Z')}",
        "",
        *("\n\n---\n\n".join(md_cards).splitlines()),
        "",
    ]
    markdown_path.write_text("\n".join(markdown), encoding="utf-8")
    return html_path, markdown_path


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(HERE.parents[1] / "scripts"))
    from build_platform_report import build_report as build_platform_report
    print(f"HTML: {build_platform_report()}")
