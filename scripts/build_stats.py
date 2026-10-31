#!/usr/bin/env python3
"""Generate the single source of truth for public statistics.

Reads the platform report and workflow catalog, writes ``data/stats.json`` and
renders the marked statistics blocks in README.md, README.zh-CN.md and
index.html. ``--check`` fails when any block or the JSON file has drifted.

Run from the repository root:

    python scripts/build_stats.py
    python scripts/build_stats.py --check
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / 'report/index.html'
PLATFORM = ROOT / 'evidence/2026-10-19-features/platform-comparison.json'
CATALOG = ROOT / 'workflows/catalog.json'
BUNDLE = ROOT / 'workflows/bundle-status.json'
CASES = ROOT / 'evidence/2026-10-19-features/cases.json'
STATS = ROOT / 'data/stats.json'

START = '<!-- STATS:START -->'
END = '<!-- STATS:END -->'


def load(path: Path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def collect() -> dict:
    platform = load(PLATFORM)
    catalog = load(CATALOG)
    bundle = load(BUNDLE)
    cases = load(CASES)
    report = REPORT.read_text(encoding='utf-8')

    cards = re.findall(r'<article class="feature"', report)
    if len(cards) != 40:
        raise SystemExit(f'expected 40 feature cards in the report, found {len(cards)}')

    records = platform['records']
    windows = platform['legacy_record_count']
    workflows = catalog['workflows']
    ui = len(workflows)
    api = sum(1 for row in workflows if row.get('api'))
    installed = bundle.get('installed_ui')

    return {
        'models': len(platform['models']),
        'features': len(cards),
        'records': {'total': len(records), 'windows': windows, 'linux': len(records) - windows},
        'workflows': {'ui': ui, 'api': api, 'installed': installed},
        'cases': len(cases),
        'report': REPORT.relative_to(ROOT).as_posix(),
    }


def markdown_en(s: dict) -> str:
    return '\n'.join([
        '| Metric | Value |',
        '|---|---:|',
        '| Model families | {models} |'.format(**s),
        '| Features documented | {features} |'.format(**s),
        '| Platform records | {r[total]} ({r[windows]} Windows + {r[linux]} Linux) |'.format(r=s['records']),
        '| Workflows | {w[ui]} UI + {w[api]} API · {w[installed]} installed |'.format(w=s['workflows']),
        '| Documented cases | {cases} |'.format(**s),
    ])


def markdown_zh(s: dict) -> str:
    return '\n'.join([
        '| 指标 | 数值 |',
        '|---|---:|',
        '| 模型系列 | {models} |'.format(**s),
        '| 功能记录 | {features} |'.format(**s),
        '| 平台记录 | {r[total]}（{r[windows]} Windows + {r[linux]} Linux） |'.format(r=s['records']),
        '| 工作流 | {w[ui]} UI + {w[api]} API · 已安装 {w[installed]} |'.format(w=s['workflows']),
        '| 记录案例 | {cases} |'.format(**s),
    ])


def html_zh(s: dict) -> str:
    return '\n'.join([
        '<ul class="ledger">',
        '<li><b>{models}</b><span>模型系列</span></li>'.format(**s),
        '<li><b>{features}</b><span>功能记录</span></li>'.format(**s),
        '<li><b>{r[total]}</b><span>平台记录（{r[windows]} Win + {r[linux]} Linux）</span></li>'.format(r=s['records']),
        '<li><b>{cases}</b><span>记录案例</span></li>'.format(**s),
        '</ul>',
    ])


def replace_block(path: Path, body: str) -> None:
    text = path.read_text(encoding='utf-8')
    pattern = re.compile(re.escape(START) + r'.*?' + re.escape(END), re.S)
    if not pattern.search(text):
        raise SystemExit(f'{path.name}: statistics markers not found')
    new = START + '\n' + body + '\n' + END
    path.write_text(pattern.sub(lambda _: new, text, count=1), encoding='utf-8')


def expected_files(s: dict) -> dict:
    return {
        ROOT / 'README.md': markdown_en(s),
        ROOT / 'README.zh-CN.md': markdown_zh(s),
        ROOT / 'index.html': html_zh(s),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true', help='fail if any generated block is stale')
    args = parser.parse_args()

    stats = collect()
    blocks = expected_files(stats)
    stats_text = json.dumps(stats, ensure_ascii=False, indent=2) + '\n'

    if args.check:
        stale = []
        if not STATS.is_file() or STATS.read_text(encoding='utf-8') != stats_text:
            stale.append('data/stats.json')
        for path, body in blocks.items():
            text = path.read_text(encoding='utf-8')
            pattern = re.compile(re.escape(START) + r'.*?' + re.escape(END), re.S)
            expected = START + '\n' + body + '\n' + END
            if not pattern.search(text) or pattern.search(text).group(0) != expected:
                stale.append(path.name)
        if stale:
            print('stale statistics blocks: ' + ', '.join(stale))
            print('run: python scripts/build_stats.py')
            return 1
        print(json.dumps({'stats': 'ok', 'files': sorted(p.name for p in blocks) + ['data/stats.json']}, indent=2))
        return 0

    STATS.parent.mkdir(exist_ok=True)
    STATS.write_text(stats_text, encoding='utf-8')
    for path, body in blocks.items():
        replace_block(path, body)
    print(json.dumps({'written': ['data/stats.json'] + sorted(p.name for p in blocks), 'stats': stats}, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
