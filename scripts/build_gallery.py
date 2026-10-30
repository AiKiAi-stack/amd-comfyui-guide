#!/usr/bin/env python3
"""Build and check the curated model-output gallery for the landing page.

Usage (from the repository root)::

    python3 scripts/build_gallery.py --build   # needs Pillow (local only)
    python3 scripts/build_gallery.py --check   # stdlib only, CI safe

``--build`` exports every curated source PNG to ``assets/gallery/<slug>.webp``
(native pixel dimensions, no EXIF/XMP/ICC metadata) and writes
``assets/gallery/manifest.json`` from the real evidence records.

``--check`` verifies the committed gallery without Pillow: the manifest parses,
all seven model families are present, every plate image exists with matching
WebP dimensions, every report anchor exists, exactly one hero per model, and no
pass/fail verdict data leaks into the gallery payload.

Each plate records ``source`` as its historical runtime capture path
(``ComfyUI/output/...``) for provenance. The PNG files themselves may live under
the historical tree or under the archived ``evidence/report-assets/output/...``
tree (see ``SOURCE_ALIASES``); ``--build`` resolves either, ``--check`` only
validates the exported WebP files and never requires a source PNG to exist.
"""

import argparse
import json
import re
import struct
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GALLERY_DIR = ROOT / "assets" / "gallery"
MANIFEST_PATH = GALLERY_DIR / "manifest.json"
DATA_PATH = ROOT / "evidence" / "2026-10-19-features" / "platform-comparison.json"
REPORT_PATH = ROOT / "evidence" / "2026-10-19-features" / "feature-report.html"

SCHEMA = 1
WEBP_QUALITY = 82
WEBP_METHOD = 6

# Model families in page order: (id, display label, short label).
MODELS = [
    ("qwen-base", "Qwen Image 2.1 · Base", "Qwen Base"),
    ("qwen-turbo", "Qwen Image 2.1 Turbo", "Qwen Turbo"),
    ("kroma", "Kroma v0.3.1 Q2_K", "Kroma"),
    ("moss", "MOSS Image SFT", "MOSS"),
    ("flux2", "FLUX.2 Klein 4B", "FLUX.2"),
    ("zimage-gguf", "Z-Image Turbo GGUF", "Z-Image GGUF"),
    ("zimage-aio", "Z-Image Turbo AIO", "Z-Image AIO"),
]
MODEL_IDS = [model[0] for model in MODELS]

# Exact curated sources, in plate order: (model_id, evidence runtime path, hero).
# Paths are the historical ComfyUI output paths stored in the evidence records;
# resolve_source() also accepts the archived evidence/report-assets copy.
CURATION = [
    ("qwen-base", "ComfyUI/output/FeatureBench/qwen-style-edit_00001_.png", False),
    ("qwen-base", "ComfyUI/output/FeatureBench/qwen-multiref_00001_.png", True),
    ("qwen-base", "ComfyUI/output/FeatureBench/qwen-inpaint_00001_.png", False),
    ("qwen-base", "ComfyUI/output/Liuyue_Qwen21_Base_Edit_RX6650XT_00001_.png", False),
    ("qwen-base", "ComfyUI/output/QwenImage21_RX6650XT_768_00001_.png", False),
    ("qwen-turbo", "ComfyUI/output/FeatureBench/turbo-un-t2i_00001_.png", True),
    ("qwen-turbo", "ComfyUI/output/FeatureBench/turbo-un-multiref_00001_.png", False),
    ("qwen-turbo", "ComfyUI/output/FeatureBench/turbo-un-role-replacement-test_00001_.png", False),
    ("qwen-turbo", "ComfyUI/output/Liuyue_Qwen21_Turbo_RX6650XT_00001_.png", False),
    ("kroma", "ComfyUI/output/FeatureBench/kroma-img2img_00001_.png", False),
    ("kroma", "ComfyUI/output/FeatureBench/kroma-style-ref_00001_.png", False),
    ("kroma", "ComfyUI/output/FeatureBench/kroma-multiref_00001_.png", False),
    ("kroma", "ComfyUI/output/FeatureBench/kroma-head-swap_00001_.png", False),
    ("kroma", "ComfyUI/output/Liuyue_Kroma031_Q2_4step_RX6650XT_00001_.png", True),
    ("moss", "ComfyUI/output/FeatureBench/moss-img2img_00001_.png", True),
    ("moss", "ComfyUI/output/FeatureBench/moss-text_00001_.png", False),
    ("moss", "ComfyUI/output/FeatureBench/moss-layout_00001_.png", False),
    ("moss", "ComfyUI/output/Liuyue_MOSS_SFT_DMD_INT8_8step_RX6650XT_00001_.png", False),
    ("flux2", "ComfyUI/output/FeatureBench/flux2-klein-style_00001_.png", True),
    ("flux2", "ComfyUI/output/FeatureBench/flux2-klein-dual-logo_00001_.png", False),
    ("flux2", "ComfyUI/output/FeatureBench/flux2-klein-replace-zh_00001_.png", False),
    ("flux2", "ComfyUI/output/FeatureBench/flux2-klein-remove_00001_.png", False),
    ("flux2", "ComfyUI/output/FeatureBench/flux2-klein-iterative_00001_.png", False),
    ("flux2", "ComfyUI/output/FeatureBench/flux2-klein-dual-people_00001_.png", False),
    ("zimage-gguf", "ComfyUI/output/FeatureBench/zimage-gguf-chinese_00001_.png", False),
    ("zimage-gguf", "ComfyUI/output/FeatureBench/zimage-gguf-photo-gpu-text_00001_.png", True),
    ("zimage-gguf", "ComfyUI/output/FeatureBench/zimage-gguf-prompt-change_00001_.png", False),
    ("zimage-gguf", "ComfyUI/output/FeatureBench/zimage-gguf-english_00001_.png", False),
    ("zimage-aio", "ComfyUI/output/FeatureBench/zimage-aio-photo-4step_00001_.png", True),
    ("zimage-aio", "ComfyUI/output/FeatureBench/zimage-aio-photo-8step_00001_.png", False),
    ("zimage-aio", "ComfyUI/output/FeatureBench/zimage-aio-chinese_00001_.png", False),
    ("zimage-aio", "ComfyUI/output/FeatureBench/zimage-aio-english_00001_.png", False),
]

# Alias roots tried after the literal evidence path: strip the leading
# ``ComfyUI/`` component and prepend each archived root.
SOURCE_ALIASES = ["evidence/report-assets"]

# Accepted manifest ``source`` provenance prefixes (historical capture tree and
# its committed archive). --check validates the shape, not file existence.
SOURCE_PREFIXES = ("ComfyUI/output/", "evidence/report-assets/output/")

# Scrub list for --check: these substrings must not appear in manifest keys, and
# these exact strings must not appear as manifest values.
FORBIDDEN_KEY_PARTS = ("verdict", "pass", "partial", "fail")
FORBIDDEN_VALUES = {"pass", "partial", "fail", "verdict", "通过", "部分达到", "失败"}
PLATE_FIELD_ORDER = (
    "id",
    "model_id",
    "feature_id",
    "feature",
    "prompt",
    "width",
    "height",
    "image",
    "source",
    "report",
    "steps",
    "sampler",
    "hero",
)
REQUIRED_PLATE_FIELDS = (
    "id",
    "model_id",
    "feature_id",
    "feature",
    "prompt",
    "width",
    "height",
    "image",
    "source",
    "report",
    "hero",
)


def rel(path):
    """Repository-relative POSIX path string."""
    return path.relative_to(ROOT).as_posix()


def source_candidates(evidence_path):
    """Yield candidate on-disk paths, historical tree first, archived tree second."""
    yield ROOT / evidence_path
    parts = Path(evidence_path).parts
    if parts and parts[0] == "ComfyUI":
        archived = Path(*parts[1:])
        for prefix in SOURCE_ALIASES:
            yield ROOT / prefix / archived


def resolve_source(evidence_path):
    """Return the first existing on-disk source PNG for a historical runtime path."""
    for candidate in source_candidates(evidence_path):
        if candidate.is_file():
            return candidate
    tried = " | ".join(rel(p) if p.is_relative_to(ROOT) else str(p) for p in source_candidates(evidence_path))
    raise SystemExit("missing source image: {}\n  tried: {}".format(evidence_path, tried))


def slug_for(evidence_path):
    """Lower-kebab slug from a source basename, dropping the _00001_ suffix."""
    stem = Path(evidence_path).name
    if stem.endswith(".png"):
        stem = stem[: -len(".png")]
    stem = re.sub(r"_00001_$", "", stem)
    slug = re.sub(r"[^a-z0-9]+", "-", stem.lower()).strip("-")
    if not slug:
        raise SystemExit("cannot derive slug for: " + evidence_path)
    return slug


def load_evidence():
    """Load platform data and map output-image basename -> record."""
    try:
        data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    except OSError as exc:
        raise SystemExit("cannot read evidence data {}: {}".format(rel(DATA_PATH), exc))
    features = data.get("features") or {}
    by_basename = {}
    for record in data.get("records") or []:
        for image in record.get("images") or []:
            name = Path(str(image).replace("\\", "/")).name
            by_basename.setdefault(name, []).append(record)
    return features, by_basename


def sampling_info(record):
    """Best-effort (steps, sampler) from recipe_conditions.sampling."""
    sampling = (record.get("recipe_conditions") or {}).get("sampling") or []
    steps = None
    sampler = None
    for node in sampling:
        if not isinstance(node, (list, tuple)) or len(node) != 2:
            continue
        label, params = node
        if not isinstance(params, dict):
            continue
        if sampler is None and isinstance(params.get("sampler_name"), str):
            sampler = params["sampler_name"]
        if steps is None and isinstance(params.get("steps"), int):
            steps = params["steps"]
        if steps is None and isinstance(params.get("noise_seed"), int) and label == "RandomNoise":
            continue
        if steps is None and label == "ManualSigmas":
            sigmas = params.get("sigmas")
            if isinstance(sigmas, str):
                values = [value for value in sigmas.split(",") if value.strip()]
                if len(values) >= 2:
                    steps = len(values) - 1
    return steps, sampler


def build_plate(model_id, evidence_path, hero, features, by_basename):
    """Collect one manifest plate from the matching evidence record."""
    basename = Path(evidence_path).name
    records = by_basename.get(basename) or []
    if len(records) != 1:
        raise SystemExit(
            "expected exactly one evidence record for {} (basename match), found {}".format(
                evidence_path, len(records)
            )
        )
    record = records[0]
    record_model = record.get("model_id")
    if record_model != model_id:
        raise SystemExit(
            "model mismatch for {}: curation says {}, record says {}".format(
                evidence_path, model_id, record_model
            )
        )
    feature_id = record.get("feature_id")
    if not feature_id or feature_id not in features:
        raise SystemExit("unknown feature_id {!r} for {}".format(feature_id, evidence_path))
    prompt = record.get("prompt")
    if not isinstance(prompt, str) or not prompt.strip():
        raise SystemExit("missing prompt in evidence record for " + evidence_path)

    source_path = resolve_source(evidence_path)
    steps, sampler = sampling_info(record)
    plate = {
        "id": slug_for(evidence_path),
        "model_id": model_id,
        "feature_id": feature_id,
        "feature": features[feature_id],
        "prompt": prompt,
        "image": None,  # filled after the source is measured
        # Provenance: the historical runtime capture path. The committed image
        # files may live under SOURCE_ALIASES; --check never requires the
        # source PNG to exist there.
        "source": evidence_path,
        "report": "evidence/2026-10-19-features/feature-report.html#{}--{}".format(
            model_id, feature_id
        ),
        "hero": bool(hero),
    }
    if steps is not None:
        plate["steps"] = int(steps)
    if sampler:
        plate["sampler"] = sampler
    return plate, source_path


def webp_metadata_chunks(path):
    """Return WebP chunk fourccs that carry metadata (for the no-metadata rule)."""
    data = path.read_bytes()
    if len(data) < 12 or data[0:4] != b"RIFF" or data[8:12] != b"WEBP":
        raise ValueError("not a WebP file: " + str(path))
    index = 12
    bad = []
    while index + 8 <= len(data):
        fourcc = data[index : index + 4]
        size = int.from_bytes(data[index + 4 : index + 8], "little")
        if fourcc in (b"EXIF", b"XMP ", b"ICCP"):
            bad.append(fourcc.decode("ascii", "replace").strip())
        index += 8 + size + (size % 2)
    return bad


def build():
    try:
        from PIL import Image
    except ImportError:
        raise SystemExit("--build needs Pillow (local only); install Pillow or use --check")

    features, by_basename = load_evidence()
    if len(MODELS) != 7:
        raise SystemExit("MODELS must contain exactly 7 model families")
    if len(CURATION) != 32:
        raise SystemExit("CURATION must contain exactly 32 curated plates")

    GALLERY_DIR.mkdir(parents=True, exist_ok=True)
    plates = []
    seen_slugs = set()
    seen_sources = set()
    heroes = 0
    for model_id, evidence_path, hero in CURATION:
        if evidence_path in seen_sources:
            raise SystemExit("duplicate curated source: " + evidence_path)
        seen_sources.add(evidence_path)
        plate, source_path = build_plate(model_id, evidence_path, hero, features, by_basename)
        if plate["id"] in seen_slugs:
            raise SystemExit("duplicate slug: " + plate["id"])
        seen_slugs.add(plate["id"])

        with Image.open(source_path) as source:
            width, height = source.size
            image = source.convert("RGB")
            target = GALLERY_DIR / (plate["id"] + ".webp")
            image.save(target, "WEBP", quality=WEBP_QUALITY, method=WEBP_METHOD)
        metadata = webp_metadata_chunks(target)
        if metadata:
            raise SystemExit("exported WebP still carries metadata chunks: {}".format(metadata))
        plate["width"] = width
        plate["height"] = height
        plate["image"] = "assets/gallery/" + target.name
        plate = {key: plate[key] for key in PLATE_FIELD_ORDER if key in plate}
        heroes += 1 if hero else 0
        plates.append(plate)
        print("wrote {} ({}x{}, {} bytes)".format(rel(target), width, height, target.stat().st_size))

    if heroes != 7:
        raise SystemExit("expected exactly one hero per model family (7), got " + str(heroes))
    hero_models = {plate["model_id"] for plate in plates if plate["hero"]}
    if hero_models != set(MODEL_IDS):
        raise SystemExit("hero plates must cover every model family")

    models = [{"id": mid, "label": label, "short": short} for mid, label, short in MODELS]
    data = {
        "schema": SCHEMA,
        "generated": date.today().isoformat(),
        "models": models,
        "plates": plates,
    }
    MANIFEST_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    total = sum((GALLERY_DIR / (plate["id"] + ".webp")).stat().st_size for plate in plates)
    largest = max(plates, key=lambda plate: (GALLERY_DIR / (plate["id"] + ".webp")).stat().st_size)
    largest_path = GALLERY_DIR / (largest["id"] + ".webp")
    print(
        "manifest: {} ({} plates, {} models, {} bytes, largest {} {} bytes)".format(
            rel(MANIFEST_PATH), len(plates), len(models), total, rel(largest_path),
            largest_path.stat().st_size,
        )
    )


# ---------------------------------------------------------------------------
# --check (stdlib only, CI safe)
# ---------------------------------------------------------------------------


def webp_dimensions(path):
    """Read (width, height) from a WebP RIFF file without Pillow."""
    data = path.read_bytes()
    if len(data) < 16 or data[0:4] != b"RIFF" or data[8:12] != b"WEBP":
        raise ValueError("not a RIFF WebP file")
    index = 12
    while index + 8 <= len(data):
        fourcc = data[index : index + 4]
        size = int.from_bytes(data[index + 4 : index + 8], "little")
        payload = data[index + 8 : index + 8 + size]
        if fourcc == b"VP8X":
            if len(payload) < 10:
                raise ValueError("truncated VP8X header")
            width = int.from_bytes(payload[4:7], "little") + 1
            height = int.from_bytes(payload[7:10], "little") + 1
            return width, height
        if fourcc == b"VP8L":
            if len(payload) < 5 or payload[0] != 0x2F:
                raise ValueError("truncated VP8L header")
            bits = int.from_bytes(payload[1:5], "little")
            return (bits & 0x3FFF) + 1, ((bits >> 14) & 0x3FFF) + 1
        if fourcc == b"VP8 ":
            if len(payload) < 10 or payload[3:6] != b"\x9d\x01\x2a":
                raise ValueError("truncated VP8 header")
            width = int.from_bytes(payload[6:8], "little") & 0x3FFF
            height = int.from_bytes(payload[8:10], "little") & 0x3FFF
            return width, height
        index += 8 + size + (size % 2)
    raise ValueError("no image bitstream chunk (VP8/VP8L/VP8X) found")


def iter_manifest_strings(node, path="$"):
    """Yield (json_path, key, value) for every string key/value in the manifest."""
    if isinstance(node, dict):
        for key, value in node.items():
            yield path, key, None
            yield from iter_manifest_strings(value, path + "." + str(key))
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from iter_manifest_strings(value, path + "[{}]".format(index))
    else:
        yield path, None, node


def report_anchors(html):
    return set(re.findall(r'<article\b[^>]*\bid="([^"]+)"', html))


def check():
    errors = []
    if not MANIFEST_PATH.is_file():
        print("FAIL: missing manifest: " + rel(MANIFEST_PATH))
        return 1
    try:
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print("FAIL: manifest does not parse: {}".format(exc))
        return 1

    if not isinstance(manifest, dict):
        errors.append("manifest root must be a JSON object")
        manifest = {}
    if manifest.get("schema") != SCHEMA:
        errors.append("manifest.schema must be {}".format(SCHEMA))
    models = manifest.get("models")
    plates = manifest.get("plates")
    if not isinstance(models, list):
        errors.append("manifest.models must be a list")
        models = []
    if not isinstance(plates, list):
        errors.append("manifest.plates must be a list")
        plates = []

    model_ids = []
    for index, model in enumerate(models):
        if not isinstance(model, dict):
            errors.append("models[{}] is not an object".format(index))
            continue
        for field in ("id", "label", "short"):
            value = model.get(field)
            if not isinstance(value, str) or not value.strip():
                errors.append("models[{}].{} must be a non-empty string".format(index, field))
        if model.get("id"):
            model_ids.append(model["id"])
    if len(set(model_ids)) != len(model_ids):
        errors.append("model ids are not unique")
    if model_ids != MODEL_IDS:
        errors.append("model ids must be exactly, in order: {}".format(", ".join(MODEL_IDS)))

    # Verdict leakage: no key may mention pass/fail/verdict, and no value may be
    # exactly a verdict word.
    for json_path, key, value in iter_manifest_strings(manifest):
        if key is not None:
            lowered = key.lower()
            for part in FORBIDDEN_KEY_PARTS:
                if part in lowered:
                    errors.append("forbidden verdict key {!r} at {}".format(key, json_path))
        elif isinstance(value, str) and value.strip().lower() in FORBIDDEN_VALUES:
            errors.append("forbidden verdict value {!r} at {}".format(value, json_path))

    try:
        anchors = report_anchors(REPORT_PATH.read_text(encoding="utf-8"))
    except OSError as exc:
        errors.append("cannot read report {}: {}".format(rel(REPORT_PATH), exc))
        anchors = set()

    report_prefix = "evidence/2026-10-19-features/feature-report.html#"
    plate_ids = set()
    model_family_ids = set(model_ids)
    heroes = 0
    hero_models = []
    for index, plate in enumerate(plates):
        where = "plates[{}]".format(index)
        if not isinstance(plate, dict):
            errors.append(where + " is not an object")
            continue
        for field in REQUIRED_PLATE_FIELDS:
            if field not in plate:
                errors.append("{}.{} is missing".format(where, field))
        plate_id = plate.get("id")
        if isinstance(plate_id, str) and plate_id:
            if plate_id in plate_ids:
                errors.append("duplicate plate id: " + plate_id)
            plate_ids.add(plate_id)
        for field in ("id", "model_id", "feature_id", "feature", "image", "source", "report"):
            value = plate.get(field)
            if not isinstance(value, str) or not value.strip():
                errors.append("{}.{} must be a non-empty string".format(where, field))
        if isinstance(plate.get("model_id"), str) and plate["model_id"] not in model_family_ids:
            errors.append("{}.model_id not in models: {}".format(where, plate["model_id"]))
        prompt = plate.get("prompt")
        if not isinstance(prompt, str) or not prompt.strip():
            errors.append(where + ".prompt must be a non-empty string")
        width, height = plate.get("width"), plate.get("height")
        if not isinstance(width, int) or width <= 0:
            errors.append(where + ".width must be a positive integer")
        if not isinstance(height, int) or height <= 0:
            errors.append(where + ".height must be a positive integer")
        if not isinstance(plate.get("hero"), bool):
            errors.append(where + ".hero must be a boolean")
        for field in ("steps", "sampler"):
            if field in plate:
                value = plate[field]
                if field == "steps" and (not isinstance(value, int) or value <= 0):
                    errors.append(where + ".steps must be a positive integer")
                if field == "sampler" and (not isinstance(value, str) or not value.strip()):
                    errors.append(where + ".sampler must be a non-empty string")

        image = plate.get("image")
        if isinstance(image, str) and image:
            if not image.startswith("assets/gallery/") or not image.endswith(".webp"):
                errors.append("{}.image must be assets/gallery/<slug>.webp, got {!r}".format(where, image))
            image_path = ROOT / image
            if not image_path.is_file():
                errors.append("{}.image is missing on disk: {}".format(where, image))
            elif isinstance(width, int) and isinstance(height, int):
                try:
                    actual_width, actual_height = webp_dimensions(image_path)
                except (OSError, ValueError) as exc:
                    errors.append("{}: cannot read WebP dimensions ({}): {}".format(where, image, exc))
                else:
                    if (actual_width, actual_height) != (width, height):
                        errors.append(
                            "{}: WebP dimensions {}x{} != manifest {}x{}".format(
                                where, actual_width, actual_height, width, height
                            )
                        )

        report = plate.get("report")
        if isinstance(report, str) and report:
            if not report.startswith(report_prefix):
                errors.append("{}.report must start with {}".format(where, report_prefix))
            else:
                anchor = report[len(report_prefix):]
                if anchors and anchor not in anchors:
                    errors.append("{}.report anchor not found in report HTML: #{}".format(where, anchor))

        source = plate.get("source")
        if isinstance(source, str) and source:
            if source.startswith("/") or re.match(r"^[A-Za-z]:", source):
                errors.append("{}.source must be repository-relative: {!r}".format(where, source))
            elif not source.startswith(SOURCE_PREFIXES):
                errors.append(
                    "{}.source must be a historical output path ({}), got {!r}".format(
                        where, " or ".join(SOURCE_PREFIXES), source
                    )
                )

        if plate.get("hero") is True:
            heroes += 1
            if isinstance(plate.get("model_id"), str):
                hero_models.append(plate["model_id"])

    if heroes != 7:
        errors.append("expected exactly 7 hero plates, found {}".format(heroes))
    if sorted(hero_models) != sorted(MODEL_IDS):
        errors.append("hero plates must cover every model family exactly once")

    if errors:
        print("FAIL: {} problem(s) in {}".format(len(errors), rel(MANIFEST_PATH)))
        for error in errors:
            print("  - " + error)
        return 1
    total = sum((ROOT / plate["image"]).stat().st_size for plate in plates)
    print(
        "OK: {} models, {} plates, 7 heroes, all images present, no verdict data".format(
            len(models), len(plates)
        )
    )
    print("  manifest: {} ({} bytes)".format(rel(MANIFEST_PATH), MANIFEST_PATH.stat().st_size))
    print("  gallery: {} files, {} bytes total".format(len(plates), total))
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--build", action="store_true", help="export WebPs and rewrite the manifest (needs Pillow)")
    group.add_argument("--check", action="store_true", help="validate the committed gallery (stdlib only)")
    args = parser.parse_args()
    if args.build:
        build()
        return 0
    return check()


if __name__ == "__main__":
    sys.exit(main())
