---
name: AMD ComfyUI Guide
description: ComfyUI on AMD Radeon GPUs — tutorial-first guide with a measured evidence set
colors:
  paper: "#0a0907"
  paper-raised: "#12100c"
  ink: "#f3eee2"
  ink-muted: "#a79d8c"
  ink-faint: "#8a8071"
  accent: "#c9a227"
  accent-bright: "#e2bd4b"
  on-accent: "#120f06"
  hairline: "rgba(243,238,226,0.14)"
  hairline-soft: "rgba(243,238,226,0.08)"
  hero-warm: "rgba(198,90,46,0.07)"
  mask: "#000"
typography:
  hero:
    fontFamily: "Alegreya, Noto Serif SC, Georgia, serif"
    fontSize: "clamp(2.55rem,5.7vw,4.85rem)"
    fontWeight: 400
    lineHeight: 1.03
    letterSpacing: "-0.032em"
  display:
    fontFamily: "Alegreya, Noto Serif SC, Georgia, serif"
    fontSize: "clamp(1.62rem,4.4vw,3.3rem)"
    fontWeight: 400
    lineHeight: 1.16
    letterSpacing: "-0.005em"
  subhead:
    fontFamily: "Alegreya, Noto Serif SC, Georgia, serif"
    fontSize: "clamp(1.5rem,3.2vw,2.55rem)"
    fontWeight: 400
    lineHeight: 1.38
    letterSpacing: "0.005em"
  body:
    fontFamily: "IBM Plex Sans, Noto Sans SC, system-ui, sans-serif"
    fontSize: "16.5px"
    fontWeight: 400
    lineHeight: 1.8
    letterSpacing: "0em"
  editorial:
    fontFamily: "IBM Plex Sans, Noto Sans SC, system-ui, sans-serif"
    fontSize: "14.5px"
    fontWeight: 400
    lineHeight: 1.85
    letterSpacing: "0em"
  label:
    fontFamily: "IBM Plex Mono, ui-monospace, monospace"
    fontSize: "11px"
    fontWeight: 500
    lineHeight: 1
    letterSpacing: "0.14em"
  meta:
    fontFamily: "IBM Plex Mono, ui-monospace, monospace"
    fontSize: "11.5px"
    fontWeight: 400
    lineHeight: 1.6
    letterSpacing: "0.04em"
  button:
    fontFamily: "IBM Plex Mono, ui-monospace, monospace"
    fontSize: "12px"
    fontWeight: 500
    lineHeight: 1
    letterSpacing: "0.13em"
  caption:
    fontFamily: "IBM Plex Sans, Noto Sans SC, system-ui, sans-serif"
    fontSize: "12.5px"
    fontWeight: 400
    lineHeight: 1.7
    letterSpacing: "0em"
  ui-small:
    fontFamily: "IBM Plex Sans, Noto Sans SC, system-ui, sans-serif"
    fontSize: "13.5px"
    fontWeight: 400
    lineHeight: 1.75
    letterSpacing: "0em"
  symbols:
    fontFamily: "UI Symbols, ui-symbols fallback for control glyphs"
    fontSize: "1em"
    fontWeight: 400
    lineHeight: 1
    letterSpacing: "0em"
rounded:
  none: "0px"
  pill: "999px"
spacing:
  pad: "clamp(20px, 4.5vw, 56px)"
  wrap: "1260px"
  section: "clamp(76px, 10vw, 132px)"
  xs: "8px"
  sm: "14px"
  md: "22px"
  lg: "clamp(28px, 4vw, 44px)"
components:
  button-primary:
    backgroundColor: "{colors.accent}"
    textColor: "{colors.on-accent}"
    rounded: "{rounded.none}"
    padding: "14px 22px"
    typography: "{typography.label}"
  button-primary-hover:
    backgroundColor: "{colors.accent-bright}"
    textColor: "{colors.on-accent}"
  button-secondary:
    backgroundColor: "transparent"
    textColor: "{colors.ink}"
    rounded: "{rounded.none}"
    padding: "14px 22px"
    typography: "{typography.label}"
  nav-cta:
    backgroundColor: "transparent"
    textColor: "{colors.ink}"
    rounded: "{rounded.none}"
    padding: "9px 13px"
    typography: "{typography.label}"
  plate-media:
    backgroundColor: "{colors.paper-raised}"
    rounded: "{rounded.none}"
    size: "fluid (4-col masonry)"
  ledger-cell:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    padding: "clamp(20px, 2.6vw, 30px)"
  lightbox-close:
    backgroundColor: "rgba(10,9,7,0.7)"
    textColor: "{colors.ink}"
    rounded: "{rounded.none}"
    padding: "8px 12px"
    typography: "{typography.label}"
---

## Overview

A darkroom archive for a field report: near-black paper, bone-coloured ink, one
gold accent, and an editorial serif that carries every large statement. The page
reads like a printed guide — hairlines instead of cards, no shadows, no rounded
corners, metadata set in monospace with wide tracking.

The surface is **Persuade** at the hero and **Read** below it: the hero earns the
visit, the rest is a catalogue of plates, chapters, downloads and records.

## Colors

- **Paper `#0a0907`** — page background; the world is lit from one side, so the
  hero carries a warm radial lift rather than a flat fill.
- **Paper raised `#12100c`** — plate media, dialog body, the vertical tint behind
  the projector.
- **Ink `#f3eee2`** — headings and body emphasis. **Ink muted `#a79d8c`** —
  supporting prose. **Ink faint `#8a8071`** — metadata only, never body copy.
- **Accent gold `#c9a227`** — one accent, used for primary action, focus ring, link
  hover and the italic emphasis inside display type. **Accent bright `#e2bd4b`** is
  its hover state only.
- **Hairlines** — `rgba(243,238,226,0.14)` for structural rules,
  `rgba(243,238,226,0.08)` for quiet ones. Borders separate, they never decorate.
- **Warm tint `rgba(198,90,46,0.07)`** — the single warm light in the hero's radial
  gradient. It is atmosphere, never a fill.
- **Mask black `#000`** — only as the opaque end of `mask-image` gradients; it is an
  opacity channel, not a palette colour.

## Typography

- **Display: Alegreya (self-hosted OFL subset, 400/400 italic).** Humanist
  calligraphic serif; italic is a real italic and is used for the emphasis run in
  the hero (`on AMD`), never for whole headings.
- **CJK display: Noto Serif SC 500/600.** Mixed headings put the Latin face first so
  Latin glyphs stay Alegreya and Chinese falls through to Noto Serif.
- **Body: IBM Plex Sans 400/500 + Noto Sans SC.** 14.5–16.5 px, line-height 1.8,
  measure capped at 58–64ch.
- **Metadata: IBM Plex Mono 400/500 at 11–11.5 px, tracking 0.04–0.22 em,
  uppercase.** It labels; it never carries prose.
- Size ramp: 11 / 11.5 / 12 / 12.5 / 13.5 / 14.5 / 16.5 px for UI text, plus fluid
  clamps for hero (2.55→4.85 rem), section title (1.62→3.3 rem) and subhead
  (1.5→2.55 rem). Tracking never exceeds −0.04 em.
- **UI Symbols** carries the three control glyphs (▶ play, ❚ pause, ✕ close) and is
  appended last in every stack.

## Layout

- One 1260 px wrap with a `clamp(20px, 4.5vw, 56px)` gutter; sections separated by
  `clamp(76px, 10vw, 132px)` vertical rhythm and a soft hairline.
- Hero: 1.12fr copy / 0.88fr projector, collapsing to one column under 980 px.
- Plates: four-column CSS masonry (three at 1100 px, two under 780 px), no fixed
  aspect ratio — the picture sets the height.
- Section heads are a single noun plus a short note on the left and an oversized
  stroked numeral on the right (decorative, `aria-hidden`, hidden under 700 px).
- Lists of downloads and chapters are hairline rows, not cards.

## Elevation & Depth

No shadows anywhere. Depth is simulated by layered paper tones (paper →
paper-raised), hairlines, and the hero's warm radial gradient. The only blur in the
system is the masthead and dialog chrome (`backdrop-filter`), used to keep type
legible over the fixed header and the dimmed gallery.

## Shapes

Squared corners throughout. The single `999px` radius belongs to the projector dot
indicators. Anything that reads as a "card" is a bordered rectangle or a hairline
row; nothing floats.

## Components

- **Button (`btn`, `btn--primary`, `btn--quiet`)** — mono uppercase label at 12 px,
  14×22 px padding, 1 px hairline border; primary is the gold fill, quiet is
  borderless and muted until hover.
- **Masthead CTA (`nav-github`)** — hairline box, label at 11 px, gold border on
  hover; the only other bordered control in the chrome.
- **Projector** — the hero's plate carousel: fixed 4/5 stage, badges top-left
  (plate counter) and top-right (the measured card), caption in display + body,
  dots and previous/next/pause controls below.
- **Plate** — image, model tag, feature caption; hover lifts a prompt excerpt and a
  plate number. Opens the lightbox.
- **Lightbox (`dialog`)** — 1.32fr media / 1fr information, mono section labels,
  prompt with copy button, parameter grid, report link.
- **Ledger** — four hairline-separated cells carrying a serif number and a mono
  label; the only place numbers are set large.
- **Footer** — display line, mono tagline, link row, and a bottom row for scope and
  copyright.

## Do's and Don'ts

**Do**

- Keep the display face on headlines and the serif italic on emphasis runs only.
- Let hairlines and spacing carry structure; keep paper tones for depth.
- Set functional text at ≥ 11 px and body copy at ≥ 12 px; keep AA contrast.
- Use the gold accent for one thing at a time: primary action, focus, or emphasis.
- Show the measured card only where an image or an evidence table does.

**Don't**

- No eyebrow or kicker above a heading — the heading carries its own weight.
- No sentence-style headings: navigation and section heads are nouns.
- No gradiented text, glass decoration, hard offset shadows, or nested cards.
- No unverifiable claims ("end to end", "all real", "no post-processing").
- No CDN: every face is a self-hosted subset built by `scripts/build_fonts.py`.
- No monospace for prose — it belongs to labels, parameters and metadata.
