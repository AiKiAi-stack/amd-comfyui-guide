#!/usr/bin/env python3
"""Build the self-hosted subset woff2 fonts for the AMD ComfyUI Guide landing page.

This is a LOCAL-ONLY build tool: ``--build`` and ``--coverage`` need fontTools
(+ brotli), which lives outside the repo in ``runs/fonttools`` (gitignored).
``--check`` and ``--download`` are stdlib-only and safe for CI.

Usage (from the repo root)::

    # one-off: fetch upstream OFL sources into runs/font-src/ (gitignored)
    python3 scripts/build_fonts.py --download

    # build assets/fonts/*.woff2 + assets/fonts/README.md + runs/design/fonts.css
    PYTHONPATH=runs/fonttools python3 scripts/build_fonts.py

    # verify every glyph used by the page / gallery prompts is covered
    PYTHONPATH=runs/fonttools python3 scripts/build_fonts.py --coverage

    # stdlib-only integrity check (CI safe)
    python3 scripts/build_fonts.py --check

Glyph coverage policy
---------------------
* Latin faces carry ASCII + Latin-1 + the common dashes/quotes/arrows used by
  the page.  CJK faces carry only CJK-range characters, so the browser
  composes mixed Chinese/Latin lines from the CSS font stacks (Latin face
  first, CJK face second).
* ``noto-serif-sc-*`` (display CJK) covers every CJK character that appears in
  ``runs/redesign-2026-10-31/copy.md`` and ``index.html``.
* ``noto-sans-sc-*`` (body CJK) covers the same set *plus* every character in
  ``assets/gallery/manifest.json`` (model labels + real prompts), because the
  gallery lightbox renders prompts in the body face.
* Characters no upstream font has (e.g. colour emoji) are reported by
  ``--coverage`` as ``system fallback`` warnings, not hard failures.

Font families / files (keep stable: index.html references them):
    Alegreya          -> alegreya-400.woff2, alegreya-400-italic.woff2
    Noto Serif SC     -> noto-serif-sc-500.woff2, noto-serif-sc-600.woff2
    IBM Plex Sans     -> ibm-plex-sans-400.woff2, ibm-plex-sans-500.woff2
    IBM Plex Mono     -> ibm-plex-mono-400.woff2, ibm-plex-mono-500.woff2
    Noto Sans SC      -> noto-sans-sc-400.woff2, noto-sans-sc-500.woff2
    UI Symbols        -> ui-symbols-400.woff2 (last-resort fallback for the
                         projector play/pause/close glyphs ▶ ❚ ✕; append
                         "UI Symbols" to the CSS stacks)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
import time
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "assets" / "fonts"
SRC_DIR = ROOT / "runs" / "font-src"
DESIGN_DIR = ROOT / "runs" / "design"
COPY_MD = ROOT / "runs" / "redesign-2026-10-31" / "copy.md"
INDEX_HTML = ROOT / "index.html"
GALLERY_MANIFEST = ROOT / "assets" / "gallery" / "manifest.json"

# Fixed timestamp for reproducible woff2 bytes (2004-01-01 UTC, font epoch).
FIXED_TS = 3156192000

# ---------------------------------------------------------------------------
# Font inventory
# ---------------------------------------------------------------------------

FONTS = [
    dict(
        key="alegreya-400",
        file="alegreya-400.woff2",
        family="Alegreya",
        subfamily="Regular",
        ps_name="Alegreya-Regular",
        weight=400,
        style="normal",
        kind="latin",
        src="alegreya/Alegreya[wght].ttf",
        axes={"wght": 400},
        size_target_kb=60,
    ),
    dict(
        key="alegreya-400-italic",
        file="alegreya-400-italic.woff2",
        family="Alegreya",
        subfamily="Italic",
        ps_name="Alegreya-Italic",
        weight=400,
        style="italic",
        kind="latin",
        src="alegreya/Alegreya-Italic[wght].ttf",
        axes={"wght": 400},
        size_target_kb=60,
    ),
    dict(
        key="ibm-plex-sans-400",
        file="ibm-plex-sans-400.woff2",
        family="IBM Plex Sans",
        subfamily="Regular",
        ps_name="IBMPlexSans-Regular",
        weight=400,
        style="normal",
        kind="latin",
        src="ibmplexsans/IBMPlexSans[wdth,wght].ttf",
        axes={"wght": 400, "wdth": 100},
        size_target_kb=30,
    ),
    dict(
        key="ibm-plex-sans-500",
        file="ibm-plex-sans-500.woff2",
        family="IBM Plex Sans",
        subfamily="Medium",
        ps_name="IBMPlexSans-Medium",
        weight=500,
        style="normal",
        kind="latin",
        src="ibmplexsans/IBMPlexSans[wdth,wght].ttf",
        axes={"wght": 500, "wdth": 100},
        size_target_kb=30,
    ),
    dict(
        key="ibm-plex-mono-400",
        file="ibm-plex-mono-400.woff2",
        family="IBM Plex Mono",
        subfamily="Regular",
        ps_name="IBMPlexMono-Regular",
        weight=400,
        style="normal",
        kind="latin",
        src="ibmplexmono/IBMPlexMono-Regular.ttf",
        size_target_kb=30,
    ),
    dict(
        key="ibm-plex-mono-500",
        file="ibm-plex-mono-500.woff2",
        family="IBM Plex Mono",
        subfamily="Medium",
        ps_name="IBMPlexMono-Medium",
        weight=500,
        style="normal",
        kind="latin",
        src="ibmplexmono/IBMPlexMono-Medium.ttf",
        size_target_kb=30,
    ),
    dict(
        key="noto-serif-sc-500",
        file="noto-serif-sc-500.woff2",
        family="Noto Serif SC",
        subfamily="Medium",
        ps_name="NotoSerifSC-Medium",
        weight=500,
        style="normal",
        kind="cjk",
        src="notoserifsc/NotoSerifSC[wght].ttf",
        axes={"wght": 500},
        size_target_kb=120,
    ),
    dict(
        key="noto-serif-sc-600",
        file="noto-serif-sc-600.woff2",
        family="Noto Serif SC",
        subfamily="SemiBold",
        ps_name="NotoSerifSC-SemiBold",
        weight=600,
        style="normal",
        kind="cjk",
        src="notoserifsc/NotoSerifSC[wght].ttf",
        axes={"wght": 600},
        size_target_kb=120,
    ),
    dict(
        key="noto-sans-sc-400",
        file="noto-sans-sc-400.woff2",
        family="Noto Sans SC",
        subfamily="Regular",
        ps_name="NotoSansSC-Regular",
        weight=400,
        style="normal",
        kind="cjk",
        src="notosanssc/NotoSansSC[wght].ttf",
        axes={"wght": 400},
        size_target_kb=260,
    ),
    dict(
        key="noto-sans-sc-500",
        file="noto-sans-sc-500.woff2",
        family="Noto Sans SC",
        subfamily="Medium",
        ps_name="NotoSansSC-Medium",
        weight=500,
        style="normal",
        kind="cjk",
        src="notosanssc/NotoSansSC[wght].ttf",
        axes={"wght": 500},
        size_target_kb=260,
    ),
    dict(
        key="ui-symbols-400",
        file="ui-symbols-400.woff2",
        family="UI Symbols",
        subfamily="Regular",
        ps_name="UISymbols-Regular",
        weight=400,
        style="normal",
        kind="symbols",
        src="notosanssymbols2/NotoSansSymbols2-Regular.ttf",
        size_target_kb=8,
    ),
]

FONT_BY_KEY = {f["key"]: f for f in FONTS}

# Upstream OFL sources (google/fonts mirror).  jsDelivr caps files at 20 MB, so
# the 25 MB Noto Serif SC variable font is fetched from raw.githubusercontent.
_JD = "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl"
_RAW = "https://raw.githubusercontent.com/google/fonts/main/ofl"

FONT_SOURCES = {
    "alegreya": {
        "urls": {
            "Alegreya[wght].ttf": f"{_RAW}/alegreya/Alegreya%5Bwght%5D.ttf",
            "Alegreya-Italic[wght].ttf": f"{_RAW}/alegreya/Alegreya-Italic%5Bwght%5D.ttf",
            "OFL.txt": f"{_RAW}/alegreya/OFL.txt",
        },
    },
    "ibmplexsans": {
        "urls": {
            "IBMPlexSans[wdth,wght].ttf": f"{_JD}/ibmplexsans/IBMPlexSans%5Bwdth,wght%5D.ttf",
            "OFL.txt": f"{_JD}/ibmplexsans/OFL.txt",
        },
    },
    "ibmplexmono": {
        "urls": {
            "IBMPlexMono-Regular.ttf": f"{_JD}/ibmplexmono/IBMPlexMono-Regular.ttf",
            "IBMPlexMono-Medium.ttf": f"{_JD}/ibmplexmono/IBMPlexMono-Medium.ttf",
            "OFL.txt": f"{_JD}/ibmplexmono/OFL.txt",
        },
    },
    "notoserifsc": {
        "urls": {
            # > 20 MB: jsDelivr refuses; raw.githubusercontent serves it.
            "NotoSerifSC[wght].ttf": f"{_RAW}/notoserifsc/NotoSerifSC%5Bwght%5D.ttf",
            "OFL.txt": f"{_JD}/notoserifsc/OFL.txt",
        },
    },
    "notosanssc": {
        "urls": {
            "NotoSansSC[wght].ttf": f"{_RAW}/notosanssc/NotoSansSC%5Bwght%5D.ttf",
            "OFL.txt": f"{_JD}/notosanssc/OFL.txt",
        },
    },
    # Small UI-symbol fallback: the text families have no ❚/✕ glyphs.
    "notosanssymbols2": {
        "urls": {
            "NotoSansSymbols2-Regular.ttf": f"{_JD}/notosanssymbols2/NotoSansSymbols2-Regular.ttf",
            "OFL.txt": f"{_JD}/notosanssymbols2/OFL.txt",
        },
    },
}

# License copies committed next to the fonts: output name -> (source dir, OFL file)
OFL_COPIES = {
    "OFL-Alegreya.txt": ("alegreya", "OFL.txt"),
    "OFL-IBMPlexSans.txt": ("ibmplexsans", "OFL.txt"),
    "OFL-IBMPlexMono.txt": ("ibmplexmono", "OFL.txt"),
    "OFL-NotoSerifSC.txt": ("notoserifsc", "OFL.txt"),
    "OFL-NotoSansSC.txt": ("notosanssc", "OFL.txt"),
    "OFL-NotoSansSymbols2.txt": ("notosanssymbols2", "OFL.txt"),
}

# ---------------------------------------------------------------------------
# Required character sets
# ---------------------------------------------------------------------------

# Latin faces: ASCII printable + Latin-1 supplement + the punctuation/arrows
# this editorial design uses.  Anything else Latin-ish found in the text
# sources is added on top; missing glyphs are simply skipped (browser falls
# back per character).
_LATIN_EXTRA = (
    "←↑→↓↔↕↖↗↘↙"          # arrows (CTA "↗", back-to-top "↑")
    "–—―‘’‚“”„†‡•…‰′″‹›«»"  # editorial dashes/quotes/bullets
    "€£¥·©®°×"              # currency / common marks
)
LATIN_CORE = (
    "".join(chr(cp) for cp in range(0x20, 0x7F))
    + "".join(chr(cp) for cp in range(0xA0, 0x100))
    + _LATIN_EXTRA
)

# Punctuation/symbol coverage forced into every CJK subset.  Noto CJK carries
# these; they keep Chinese sentences correct even if the Latin faces change.
_CJK_PUNCT = (
    "、。〈〉《》「」『』【】〔〕〖〗〘〙〚〛〜・"
    "…—–‘’“”※→←↑↓↔↕↖↗↘↙"
    "●○◆◇■□▲△▼▽★☆·～"
    "！＂＃＄％＆（）＊＋，－．／：；＜＝＞？＠［］＾＿｀｛｜｝"
    "\u3000"  # ideographic space
)
CJK_PUNCT_CODEPOINTS = frozenset(ord(c) for c in _CJK_PUNCT)

CJK_RANGE_START = 0x2E80  # CJK radicals and everything above is "CJK-ish"

# UI control glyphs used by the page (`▶` / `❚❚` projector controls, `✕`
# lightbox close).  None of the four text families carry `❚`/`✕`, so a 1-2 KB
# "UI Symbols" face is built from Noto Sans Symbols 2 (OFL) and appended to the
# CSS stacks.  Keep this list small: it is a UI fallback, not a general font.
UI_SYMBOLS = "▶❚✕⏸⏯⏵⏴◀◼◾▸▾✓✗■□●○◆◇★☆→←↑↓↗↘"
UI_SYMBOLS_CODEPOINTS = frozenset(ord(c) for c in UI_SYMBOLS)

# CSS stacks the coverage check simulates (Latin face first, CJK face second,
# UI symbol fallback last).
DISPLAY_STACK = ["alegreya-400", "alegreya-400-italic",
                 "noto-serif-sc-500", "noto-serif-sc-600", "ui-symbols-400"]
BODY_STACK = ["ibm-plex-sans-400", "ibm-plex-sans-500",
              "noto-sans-sc-400", "noto-sans-sc-500", "ui-symbols-400"]
MONO_STACK = ["ibm-plex-mono-400", "ibm-plex-mono-500", "noto-sans-sc-400",
              "ui-symbols-400"]

# Characters above this codepoint (emoji etc.) are allowed to fall back to the
# platform emoji font instead of failing coverage.
SYSTEM_FALLBACK_START = 0x1F000

DISPLAY_CLASS_RE = re.compile(
    r"(display|head|title|eyebrow|kicker|lede|hero|quote|caption|plate|"
    r"number|label|brand|motto|index|h[1-6])",
    re.IGNORECASE,
)

SKIP_TAGS = {"script", "style", "noscript", "template"}


# ---------------------------------------------------------------------------
# Text extraction
# ---------------------------------------------------------------------------

class _HTMLScan(HTMLParser):
    """Collect rendered text, display-ish text and inline script text."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.visible: list[str] = []
        self.display: list[str] = []
        self.script: list[str] = []
        self._stack: list[tuple[str, bool, bool]] = []
        self._skip = 0
        self._in_script = False

    def handle_starttag(self, tag, attrs):
        if tag in SKIP_TAGS:
            if tag == "script":
                self._in_script = True
            self._skip += 1
            return
        if self._skip:
            return
        ad = dict(attrs)
        marker = (ad.get("class") or "") + " " + (ad.get("id") or "")
        is_heading = tag in {"h1", "h2", "h3", "h4", "h5", "h6"}
        is_display = is_heading or bool(DISPLAY_CLASS_RE.search(marker))
        self._stack.append((tag, is_heading, is_display))

    def handle_startendtag(self, tag, attrs):
        # Self-closing / void tags (img, br, meta, ...) never carry text.
        return

    def handle_endtag(self, tag):
        if tag in SKIP_TAGS:
            if tag == "script":
                self._in_script = False
            self._skip = max(0, self._skip - 1)
            return
        if self._skip:
            return
        for i in range(len(self._stack) - 1, -1, -1):
            if self._stack[i][0] == tag:
                del self._stack[i:]
                break

    def handle_data(self, data):
        if self._in_script:
            self.script.append(data)
            return
        if self._skip:
            return
        self.visible.append(data)
        if any(h or d for _, h, d in self._stack):
            self.display.append(data)

    def text(self) -> tuple[str, str, str]:
        return ("\n".join(self.visible), "\n".join(self.display),
                "\n".join(self.script))


def _scan_html(path: Path) -> tuple[str, str, str]:
    parser = _HTMLScan()
    parser.feed(path.read_text(encoding="utf-8"))
    return parser.text()


def _json_strings(node) -> list[str]:
    out: list[str] = []
    if isinstance(node, str):
        out.append(node)
    elif isinstance(node, dict):
        for value in node.values():
            out.extend(_json_strings(value))
    elif isinstance(node, list):
        for item in node:
            out.extend(_json_strings(item))
    return out


class TextSources:
    """All text that the built fonts need to cover, split per source."""

    def __init__(self) -> None:
        self.parts: dict[str, str] = {}
        self.display: dict[str, str] = {}
        self.present: dict[str, bool] = {}

    def add(self, name: str, text: str, display: str | None = None) -> None:
        self.parts[name] = text
        self.display[name] = display if display is not None else ""
        self.present[name] = True

    def all_text(self) -> str:
        return "\n".join(self.parts.values())

    def display_text(self) -> str:
        return "\n".join(self.display.values())

    def manifest_text(self) -> str:
        return self.parts.get("gallery-manifest.json", "")


def collect_text_sources() -> TextSources:
    sources = TextSources()
    if COPY_MD.exists():
        sources.add("copy.md", COPY_MD.read_text(encoding="utf-8"))
    if INDEX_HTML.exists():
        visible, display, script = _scan_html(INDEX_HTML)
        # Runtime strings inside <script> (filter labels, counters) are shown
        # on screen, so they count towards the body coverage set.
        sources.add("index.html", visible + "\n" + script, display)
    if GALLERY_MANIFEST.exists():
        try:
            manifest = json.loads(GALLERY_MANIFEST.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:  # pragma: no cover - defensive
            print(f"warning: cannot read {GALLERY_MANIFEST.relative_to(ROOT)}: {exc}",
                  file=sys.stderr)
        else:
            sources.add("gallery-manifest.json", "\n".join(_json_strings(manifest)))
    return sources


def latin_unicodes(*texts: str) -> set[int]:
    cps = {ord(c) for c in LATIN_CORE}
    for text in texts:
        cps.update(ord(c) for c in text if ord(c) < CJK_RANGE_START)
    return cps


def cjk_unicodes(*texts: str) -> set[int]:
    cps = set(CJK_PUNCT_CODEPOINTS)
    for text in texts:
        cps.update(ord(c) for c in text if ord(c) >= CJK_RANGE_START)
    return cps


# ---------------------------------------------------------------------------
# fontTools plumbing (local only)
# ---------------------------------------------------------------------------

def _import_fonttools():
    """Import fontTools/brotli, falling back to the local runs/fonttools dir."""
    try:
        import fontTools  # noqa: F401
        import brotli  # noqa: F401
        return
    except ImportError:
        pass
    local = ROOT / "runs" / "fonttools"
    if local.is_dir():
        sys.path.insert(0, str(local))
    try:
        import fontTools  # noqa: F401
        import brotli  # noqa: F401
    except ImportError as exc:  # pragma: no cover - environment guard
        raise SystemExit(
            "fontTools/brotli not available. Run with "
            "`PYTHONPATH=runs/fonttools python3 scripts/build_fonts.py` "
            f"(original error: {exc})"
        ) from exc


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _clean_names(font, cfg: dict) -> None:
    """Replace the name table with a minimal, deterministic set of records."""
    from fontTools.ttLib.tables._n_a_m_e import NameRecord, table__n_a_m_e

    family = cfg["family"]
    subfamily = cfg["subfamily"]
    full_name = family if subfamily == "Regular" else f"{family} {subfamily}"
    ps_name = cfg["ps_name"]
    version = "Version 1.000; subset"

    table = table__n_a_m_e()
    for name_id, value in (
        (1, family),
        (2, subfamily),
        (3, f"{ps_name};{version}"),
        (4, full_name),
        (5, version),
        (6, ps_name),
    ):
        record = NameRecord()
        record.nameID = name_id
        record.platformID = 3  # Windows
        record.platEncID = 1  # Unicode BMP
        record.langID = 0x409  # en-US
        record.string = value.encode("utf-16-be")
        table.names.append(record)
    font["name"] = table


def _patch_metrics(font, cfg: dict) -> None:
    weight = cfg["weight"]
    italic = cfg["style"] == "italic"
    os2 = font["OS/2"]
    os2.usWeightClass = weight
    if italic:
        os2.fsSelection |= 1 << 0  # ITALIC
        os2.fsSelection &= ~(1 << 6)  # not REGULAR
        font["head"].macStyle |= 1 << 1
    else:
        os2.fsSelection &= ~(1 << 0)
        font["head"].macStyle &= ~(1 << 1)
    font["head"].fontRevision = 1.0
    font["head"].created = FIXED_TS
    font["head"].modified = FIXED_TS
    if "post" in font and hasattr(font["post"], "isFixedPitch"):
        font["post"].isFixedPitch = 1 if cfg["family"] == "IBM Plex Mono" else 0


def build_font(cfg: dict, latin_cps: set[int], serif_cps: set[int],
               sans_cps: set[int]) -> dict:
    """Subset + instantiate one face, write the woff2, return its stats."""
    _import_fonttools()
    from fontTools import subset
    from fontTools.ttLib import TTFont
    from fontTools.varLib import instancer

    src_path = SRC_DIR / cfg["src"]
    if not src_path.exists():
        raise SystemExit(
            f"missing source font {src_path.relative_to(ROOT)} — run "
            "`python3 scripts/build_fonts.py --download` first"
        )

    started = time.time()
    font = TTFont(str(src_path), recalcBBoxes=False, recalcTimestamp=False)
    cmap = font.getBestCmap()

    if cfg["kind"] == "latin":
        wanted = latin_cps
    elif cfg["kind"] == "symbols":
        wanted = UI_SYMBOLS_CODEPOINTS
    elif cfg["key"].startswith("noto-serif-sc"):
        wanted = serif_cps
    else:
        wanted = sans_cps
    unicodes = sorted(cp for cp in wanted if cp in cmap)

    # Subset before instancing: the variable font shrinks from ~31k glyphs to
    # a few hundred, which makes instancing + compression an order of
    # magnitude faster while producing identical outlines.
    options = subset.Options()
    options.layout_features = ["*"]
    options.name_IDs = ["1", "2", "3", "4", "6"]
    options.name_languages = ["en"]
    options.notdef_outline = True
    options.hinting = True
    options.glyph_names = False
    options.recalc_timestamp = False
    options.ignore_missing_unicodes = True
    options.drop_tables = list(options.drop_tables) + ["meta"]
    subsetter = subset.Subsetter(options=options)
    subsetter.populate(unicodes=unicodes)
    subsetter.subset(font)

    if cfg.get("axes"):
        font = instancer.instantiateVariableFont(
            font, dict(cfg["axes"]), inplace=True, optimize=True
        )
    for tag in ("fvar", "gvar", "avar", "HVAR", "MVAR", "STAT", "cvar", "VVAR"):
        if tag in font:
            del font[tag]

    _clean_names(font, cfg)
    _patch_metrics(font, cfg)

    tmp_path = OUT_DIR / (cfg["file"] + ".part")
    font.flavor = "woff2"
    font.save(str(tmp_path))
    font.close()
    tmp_path.replace(OUT_DIR / cfg["file"])

    out_path = OUT_DIR / cfg["file"]
    return {
        "key": cfg["key"],
        "file": cfg["file"],
        "family": cfg["family"],
        "subfamily": cfg["subfamily"],
        "weight": cfg["weight"],
        "style": cfg["style"],
        "kind": cfg["kind"],
        "bytes": out_path.stat().st_size,
        "glyphs": len(unicodes),
        "unicodes": unicodes,
        "seconds": round(time.time() - started, 2),
        "sha256": _sha256(out_path),
        "src": cfg["src"],
        "src_sha256": _sha256(src_path),
    }


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------

def _copy_licenses() -> list[str]:
    written = []
    for dest_name, (src_dir, ofl_name) in OFL_COPIES.items():
        src = SRC_DIR / src_dir / ofl_name
        if not src.exists():
            raise SystemExit(f"missing license source {src.relative_to(ROOT)}")
        dest = OUT_DIR / dest_name
        shutil.copyfile(src, dest)
        written.append(dest_name)
    return written


def _write_fonts_css(stats: list[dict]) -> Path:
    lines = [
        "/* Auto-generated by scripts/build_fonts.py — do not edit by hand. */",
        "/* Self-hosted subset faces; URLs are relative to the repository root",
        "   (index.html lives at the root). Rebuild: see assets/fonts/README.md. */",
        "",
    ]
    for st in stats:
        cfg = FONT_BY_KEY[st["key"]]
        lines.extend([
            "@font-face {",
            f'  font-family: "{cfg["family"]}";',
            f'  src: url("assets/fonts/{cfg["file"]}") format("woff2");',
            f'  font-weight: {cfg["weight"]};',
            f'  font-style: {cfg["style"]};',
            "  font-display: swap;",
            "}",
            "",
        ])
    path = DESIGN_DIR / "fonts.css"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def _kb(num_bytes: int) -> str:
    return f"{num_bytes / 1024:.1f} KB"


def _write_readme(stats: list[dict]) -> Path:
    by_family: dict[str, list[dict]] = {}
    for st in stats:
        by_family.setdefault(st["family"], []).append(st)
    total = sum(st["bytes"] for st in stats)

    lines = [
        "# Self-hosted fonts — AMD ComfyUI Guide",
        "",
        "Subset `woff2` files for the landing page. No font CDN, no runtime",
        "downloads: `index.html` references these files with `@font-face`",
        "(relative `assets/fonts/...` URLs) and `font-display: swap`.",
        "",
        "**Direction:** *Darkroom Archive* — editorial serif display (Latin",
        "*Alegreya*, CJK *Noto Serif SC*), refined body sans (Latin",
        "*IBM Plex Sans*, CJK *Noto Sans SC*), and *IBM Plex Mono* for metadata,",
        "eyebrows and plate numbers.",
        "",
        f"**Total:** {len(stats)} files, {total} bytes ({_kb(total)}).",
        "",
        "## Inventory",
        "",
        "| File | Family | Weight | Style | Glyphs | Bytes |",
        "|---|---|---:|---|---:|---:|",
    ]
    for st in stats:
        lines.append(
            f"| `{st['file']}` | {st['family']} | {st['weight']} | "
            f"{st['style']} | {st['glyphs']} | {st['bytes']} ({_kb(st['bytes'])}) |"
        )

    lines += [
        "",
        "## Provenance",
        "",
        "All families are licensed under the SIL Open Font License 1.1. Sources",
        "are the Google Fonts mirror (`github.com/google/fonts`); license texts",
        "are committed next to the fonts as `OFL-*.txt`.",
        "",
        "| Family | Upstream file | Source URL |",
        "|---|---|---|",
    ]
    seen: set[tuple[str, str]] = set()
    for cfg in FONTS:
        source = FONT_SOURCES[cfg["src"].split("/")[0]]["urls"][cfg["src"].split("/", 1)[1]]
        family = cfg["family"]
        key = (family, cfg["src"])
        if key in seen:
            continue
        seen.add(key)
        lines.append(f"| {family} | `{cfg['src']}` | <{source}> |")

    lines += [
        "",
        "## Font stacks",
        "",
        "```css",
        ':root {',
        "  --font-display: \"Alegreya\", \"Noto Serif SC\", \"UI Symbols\", \"Songti SC\", Georgia, serif;",
        '  --font-body: "IBM Plex Sans", "Noto Sans SC", "UI Symbols", "PingFang SC", "Microsoft YaHei", system-ui, sans-serif;',
        '  --font-mono: "IBM Plex Mono", "UI Symbols", ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;',
        "}",
        "```",
        "",
        "`UI Symbols` only carries the handful of control glyphs the text",
        "families lack (`▶` play, `❚` pause, `✕` close); it is 1-2 KB and must",
        "come *after* the text faces in each stack.",
        "",
        "Latin faces come first so mixed Chinese/Latin text gets Latin serif/",
        "sans glyphs; CJK faces carry only CJK-range glyphs and fill the rest.",
        "Attribute-level typography (sizes, tracking, motion) is specified in",
        "`runs/design/typography-spec.md`.",
        "",
        "## Rebuild",
        "",
        "```bash",
        "# 1. fetch OFL sources (cached in runs/font-src/, gitignored; ~45 MB)",
        "python3 scripts/build_fonts.py --download",
        "# 2. subset + emit woff2 (needs fontTools + brotli from runs/fonttools)",
        "PYTHONPATH=runs/fonttools python3 scripts/build_fonts.py",
        "# 3. verify page/gallery glyph coverage (fontTools)",
        "PYTHONPATH=runs/fonttools python3 scripts/build_fonts.py --coverage",
        "# 4. stdlib-only integrity check (CI safe, no third-party imports)",
        "python3 scripts/build_fonts.py --check",
        "```",
        "",
        "The builder extracts its glyph set from",
        "`runs/redesign-2026-10-31/copy.md`, `index.html` and (when present)",
        "`assets/gallery/manifest.json`. Re-run step 2 + 3 whenever page copy",
        "or gallery prompts change so no glyph silently falls back to a system",
        "font.",
        "",
        "## Subset policy",
        "",
        "- Latin subset: ASCII printable, Latin-1 supplement, editorial dashes /",
        "  quotes / bullets, and the arrows used by CTAs (`↗`) and back-to-top",
        "  (`↑`), plus any Latin character found in the page text.",
        "- CJK serif subset: CJK characters from `copy.md` + `index.html` (all",
        "  display text) plus CJK punctuation and common symbols.",
        "- CJK sans subset: the serif set **plus** every character in the gallery",
        "  manifest (model labels and real prompts shown in the lightbox).",
        "- OpenType layout (`GSUB`/`GPOS`, all features) is preserved so kerning",
        "  and punctuation shaping stay correct.",
        "",
        "## Build metadata",
        "",
        "Deterministic output (fixed `head` timestamps, minimal name table,",
        "sorted Unicode sets), so repeated builds produce identical bytes.",
        "",
        "| File | Bytes | SHA-256 | Upstream source SHA-256 |",
        "|---|---:|---|---|",
    ]
    for st in stats:
        lines.append(
            f"| `{st['file']}` | {st['bytes']} | `{st['sha256'][:16]}…` | "
            f"`{st['src_sha256'][:16]}…` |"
        )
    lines.append("")

    path = OUT_DIR / "README.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def cmd_build() -> int:
    _import_fonttools()
    if not SRC_DIR.is_dir():
        raise SystemExit(
            "runs/font-src/ is missing — run "
            "`python3 scripts/build_fonts.py --download` first"
        )
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    DESIGN_DIR.mkdir(parents=True, exist_ok=True)

    sources = collect_text_sources()
    all_text = sources.all_text()
    copy_text = sources.parts.get("copy.md", "")
    index_visible = ""
    index_display = ""
    if "index.html" in sources.parts:
        _, index_display, _ = _scan_html(INDEX_HTML)
        index_visible = sources.parts["index.html"]

    latin_cps = latin_unicodes(all_text)
    # Serif display must be able to render anything in the page/copy (any of
    # it might be set in the editorial serif); prompts stay on the sans face.
    serif_cps = cjk_unicodes(copy_text, index_visible)
    sans_cps = cjk_unicodes(all_text)

    print("== text sources")
    for name, text in sources.parts.items():
        cjk = sum(1 for c in set(text) if ord(c) >= CJK_RANGE_START)
        print(f"   {name}: {len(text):>7} chars, {len(set(text)):>4} unique, {cjk:>4} CJK unique")
    print(f"   latin glyph set: {len(latin_cps)} codepoints")
    print(f"   serif glyph set: {len(serif_cps)} codepoints (copy.md + index.html)")
    print(f"   sans  glyph set: {len(sans_cps)} codepoints (+ gallery prompts)")
    print()

    stats: list[dict] = []
    print("== building woff2 subsets")
    for cfg in FONTS:
        st = build_font(cfg, latin_cps, serif_cps, sans_cps)
        stats.append(st)
        budget = cfg["size_target_kb"] * 1024
        flag = "OK" if st["bytes"] <= budget else "OVER budget (informational)"
        print(
            f"   {st['file']:<32} {st['family']:<17} {st['weight']:>3} "
            f"{st['glyphs']:>4} glyphs  {st['bytes']:>7} B  "
            f"target<{cfg['size_target_kb']}KB  {flag}  ({st['seconds']}s)"
        )

    licenses = _copy_licenses()
    css_path = _write_fonts_css(stats)
    readme_path = _write_readme(stats)

    total = sum(st["bytes"] for st in stats)
    over = [st for st in stats if st["bytes"] > FONT_BY_KEY[st["key"]]["size_target_kb"] * 1024]
    print()
    print(f"== wrote {len(stats)} woff2 files, {total} bytes ({_kb(total)}) to "
          f"{OUT_DIR.relative_to(ROOT)}/")
    print(f"   licenses: {', '.join(licenses)}")
    print(f"   @font-face css: {css_path.relative_to(ROOT)}")
    print(f"   asset README:   {readme_path.relative_to(ROOT)}")
    if over:
        print(f"   note: {len(over)} file(s) above the soft size budget: "
              + ", ".join(st["file"] for st in over))
        print("   (still small enough for the page; budget is a target, not a hard cap)")
    print("== next: run --coverage to prove page/gallery glyph coverage")
    return 0


# ---------------------------------------------------------------------------
# Coverage (local only)
# ---------------------------------------------------------------------------

def _load_cmap(path: Path) -> set[int]:
    from fontTools.ttLib import TTFont

    font = TTFont(str(path), lazy=True)
    try:
        return set(font.getBestCmap().keys())
    finally:
        font.close()


def _covered(cps_by_face: dict[str, set[int]], stack: list[str]) -> set[int]:
    covered: set[int] = set()
    for key in stack:
        covered |= cps_by_face[key]
    return covered


def _describe_missing(missing: set[int]) -> str:
    return " ".join(f"{chr(cp)}(U+{cp:04X})" for cp in sorted(missing))


def cmd_coverage() -> int:
    _import_fonttools()
    failures = 0

    cps_by_face: dict[str, set[int]] = {}
    print("== font cmaps")
    for cfg in FONTS:
        path = OUT_DIR / cfg["file"]
        if not path.exists():
            print(f"   MISSING FILE {cfg['file']} (run --build)")
            return 1
        cmap = _load_cmap(path)
        cps_by_face[cfg["key"]] = cmap
        print(f"   {cfg['file']:<32} {len(cmap):>4} codepoints  {path.stat().st_size:>7} B")

    sources = collect_text_sources()
    if "index.html" not in sources.parts:
        print("   note: index.html absent — coverage checked against copy.md only")

    def check(label: str, text: str, stack: list[str], allow_system: bool = True) -> None:
        nonlocal failures
        chars = {ord(c) for c in text if c not in "\n\r\t" and not c.isspace() or c == " "}
        missing = chars - _covered(cps_by_face, stack)
        hard = {cp for cp in missing if cp < SYSTEM_FALLBACK_START}
        soft = missing - hard
        status = "OK" if not hard else "FAIL"
        print(f"   {label:<46} {len(chars):>4} unique chars  {status}")
        if hard:
            failures += 1
            print(f"      missing from stack: {_describe_missing(hard)}")
        if soft and allow_system:
            print(f"      system fallback (emoji etc.): {_describe_missing(soft)}")

    print()
    print("== CSS stack coverage")
    display_text = sources.display_text()
    check("display stack: copy.md + index.html display", sources.parts.get("copy.md", "") + "\n" + display_text, DISPLAY_STACK)
    check("body stack: copy.md + index.html + prompts", sources.all_text(), BODY_STACK)
    mono_extra = sources.parts.get("copy.md", "") + "\n" + sources.parts.get("index.html", "")
    check("mono stack: copy.md + index.html", mono_extra, MONO_STACK)

    print()
    print("== CJK subset ownership")
    copy_text = sources.parts.get("copy.md", "")
    index_text = sources.parts.get("index.html", "")
    manifest_text = sources.manifest_text()
    page_cjk = {ord(c) for c in copy_text + index_text if ord(c) >= CJK_RANGE_START}
    all_cjk = {ord(c) for c in sources.all_text() if ord(c) >= CJK_RANGE_START}

    def check_set(label: str, needed: set[int], face_key: str) -> None:
        nonlocal failures
        missing = sorted(needed - cps_by_face[face_key])
        status = "OK" if not missing else "FAIL"
        print(f"   {label:<46} {len(needed):>4} chars  {status}")
        if missing:
            failures += 1
            print(f"      missing: {_describe_missing(set(missing))}")

    check_set("Noto Serif SC 500 ← copy.md + index.html", page_cjk, "noto-serif-sc-500")
    check_set("Noto Serif SC 600 ← copy.md + index.html", page_cjk, "noto-serif-sc-600")
    check_set("Noto Sans SC 400 ← page + gallery prompts", all_cjk, "noto-sans-sc-400")
    check_set("Noto Sans SC 500 ← page + gallery prompts", all_cjk, "noto-sans-sc-500")
    check_set(
        "UI Symbols ← projector/lightbox controls",
        frozenset(ord(c) for c in "▶❚✕"),
        "ui-symbols-400",
    )

    print()
    if failures:
        print(f"== COVERAGE FAILED: {failures} check(s) with missing glyphs")
        print("   rebuild after the copy settles: PYTHONPATH=runs/fonttools "
              "python3 scripts/build_fonts.py")
        return 1
    print("== coverage OK: every page/gallery character is covered by a shipped face")
    return 0


# ---------------------------------------------------------------------------
# Stdlib-only check (CI safe)
# ---------------------------------------------------------------------------

def cmd_check() -> int:
    problems: list[str] = []
    warned: list[str] = []
    total = 0
    print("== assets/fonts integrity check (stdlib only)")
    print(f"   {OUT_DIR.relative_to(ROOT) if OUT_DIR.exists() else OUT_DIR}:")
    for cfg in FONTS:
        path = OUT_DIR / cfg["file"]
        if not path.exists():
            problems.append(f"missing font file {path.relative_to(ROOT)}")
            print(f"   MISSING  {cfg['file']}")
            continue
        size = path.stat().st_size
        total += size
        with path.open("rb") as handle:
            magic = handle.read(4)
        if magic != b"wOF2":
            problems.append(f"{cfg['file']} is not a WOFF2 file (magic {magic!r})")
        if size < 1024:
            problems.append(f"{cfg['file']} suspiciously small ({size} B)")
        budget = cfg["size_target_kb"] * 1024
        if size > budget:
            warned.append(f"{cfg['file']} {size} B > soft budget {budget} B")
        print(f"   OK  {cfg['file']:<34} {size:>7} B  ({_kb(size)})")

    print(f"   total: {len(FONTS)} faces, {total} B ({_kb(total)})")

    for dest_name in OFL_COPIES:
        path = OUT_DIR / dest_name
        if not path.exists():
            problems.append(f"missing license file {path.relative_to(ROOT)}")
        elif "SIL OPEN FONT LICENSE" not in path.read_text(encoding="utf-8", errors="replace"):
            problems.append(f"{dest_name} does not contain an OFL header")
    if all((OUT_DIR / name).exists() for name in OFL_COPIES):
        print(f"   OK  licenses: {', '.join(OFL_COPIES)}")

    readme = OUT_DIR / "README.md"
    if not readme.exists():
        problems.append("missing assets/fonts/README.md")
    else:
        text = readme.read_text(encoding="utf-8")
        for cfg in FONTS:
            if cfg["file"] not in text:
                problems.append(f"assets/fonts/README.md does not list {cfg['file']}")
        print("   OK  README.md inventory")

    if INDEX_HTML.exists():
        referenced = set(
            re.findall(r'url\([\'"]?(assets/fonts/[^\'")]+\.woff2)', INDEX_HTML.read_text(encoding="utf-8"))
        )
        known = {f"assets/fonts/{cfg['file']}" for cfg in FONTS}
        missing_refs = referenced - known
        if missing_refs:
            problems.append("index.html references unknown font file(s): " + ", ".join(sorted(missing_refs)))
        unused = known - referenced
        print(f"   {'OK' if not missing_refs else 'FAIL'}  index.html @font-face references: "
              f"{len(referenced)} found")
        if unused:
            print("   note: built but not referenced by index.html: "
                  + ", ".join(sorted(Path(u).name for u in unused)))

    for warning in warned:
        print(f"   warn: {warning}")

    print()
    if problems:
        print(f"== CHECK FAILED ({len(problems)} problem(s))")
        for problem in problems:
            print(f"   - {problem}")
        return 1
    print("== check OK: all expected font, license and README files are present")
    return 0


# ---------------------------------------------------------------------------
# Download (stdlib only)
# ---------------------------------------------------------------------------

def _download(url: str, dest: Path, attempts: int = 4) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "amd-comfyui-guide-font-build/1.0"})
            with urllib.request.urlopen(request, timeout=180) as response:  # noqa: S310 - fixed OFL URLs
                data = response.read()
            if not data:
                raise OSError("empty response")
            dest.write_bytes(data)
            print(f"   OK  {dest.relative_to(ROOT)}  {len(data)} B")
            return
        except Exception as exc:  # noqa: BLE001 - retry all network failures
            last_error = exc
            print(f"   retry {attempt}/{attempts} {dest.name}: {exc}")
            time.sleep(2 * attempt)
    raise SystemExit(f"failed to download {url}: {last_error}")


def cmd_download() -> int:
    print("== downloading OFL font sources into runs/font-src/ (gitignored)")
    for src_dir, spec in FONT_SOURCES.items():
        for name, url in spec["urls"].items():
            dest = SRC_DIR / src_dir / name
            if dest.exists() and dest.stat().st_size > 0:
                print(f"   have {dest.relative_to(ROOT)}  {dest.stat().st_size} B")
                continue
            _download(url, dest)
    print(f"== sources ready under {SRC_DIR.relative_to(ROOT)}/")
    return 0


# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build + verify self-hosted subset fonts for the landing page."
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--build", action="store_true", help="build woff2 subsets (needs fontTools)")
    group.add_argument("--coverage", action="store_true", help="verify page/gallery glyph coverage (needs fontTools)")
    group.add_argument("--check", action="store_true", help="stdlib-only integrity check (CI safe)")
    group.add_argument("--download", action="store_true", help="download upstream OFL sources")
    args = parser.parse_args(argv)

    if args.download:
        return cmd_download()
    if args.check:
        return cmd_check()
    if args.coverage:
        return cmd_coverage()
    # --build is the default action.
    return cmd_build()


if __name__ == "__main__":
    sys.exit(main())
