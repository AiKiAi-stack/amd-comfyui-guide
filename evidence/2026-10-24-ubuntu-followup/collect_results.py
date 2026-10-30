"""Summarize completed followup runs without changing their raw records."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--run', nargs='+', required=True)
    args = parser.parse_args()
    records = []
    for name in args.run:
        root = ROOT / 'runs' / name
        path = root / 'summary.json'
        summary = json.loads(path.read_text())
        memory = [json.loads(line) for line in (root / 'memory.jsonl').read_text().splitlines()]
        phases = summary['phases']
        records.append({'run': name, 'raw_summary_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            'status': summary['status'], 'error': summary.get('error'), 'pid': summary['pid'],
            'server_exit_code': summary.get('server_exit_code'),
            'server_stopped': summary.get('server_stopped'),
            'clip_cpu_backing': summary['clip_cpu_backing'], 'encode_only': summary['encode_only'],
            'whole_graph': summary.get('direct_graph', False),
            'defer_vae': summary.get('defer_vae', False),
            'omit_unused_vae': summary['omit_unused_vae'],
            'host_trim': summary['host_trim'],
            'minimum_available_ram_mib': min(x['available_bytes'] for x in memory) / 1024**2,
            'maximum_rss_mib': max(x['server_rss'] for x in memory) / 1024**2,
            'phase_seconds': {p['id']: p.get('seconds') for p in phases},
            'gpu_active_release_checks_passed': sum(p.get('explicit_unload', {}).get('gpu_active_below_256_mib', False) for p in phases),
            'gpu_reserved_release_checks_passed': sum(p.get('explicit_unload', {}).get('gpu_reserved_below_256_mib', False) for p in phases),
            'images': summary['images'],
            'source_hashes_at_startup': summary['runtime_source_sha256'],
            'runner_sha256_at_startup': summary['runner_sha256_at_startup']})
    with args.out.open('x') as stream:
        json.dump(records, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    print([(r['run'], r['status'], round(r['minimum_available_ram_mib'], 1)) for r in records])


if __name__ == '__main__':
    main()
