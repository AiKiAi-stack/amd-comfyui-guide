"""Prepare portable case graphs and dependencies for real frontend conversion."""
import argparse
import copy
import json
import os
from pathlib import Path, PurePosixPath
import re
import shlex
import shutil
from urllib.request import urlopen

from platform_catalog import ROOT, MODELS, FEATURES, catalog_records, sha, standalone_graph

LIBRARY = ROOT / 'workflows'
TRIAL = ROOT / 'trials/2026-10-24-platform-report'
MODEL_FIELDS = {'unet_name', 'clip_name', 'clip_name1', 'clip_name2', 'vae_name', 'ckpt_name', 'lora_name', 'clip_proj_name'}
ARCHIVE_LOADERS = ('LoadRepairConditioning', 'LoadRepairLatent', 'LoadRepairText')
PHASE_LABELS = {'caption': '反推', 'encode': '编码', 'sample': '采样'}


def safe_name(value):
    return re.sub(r'[<>:"/\\|?*\x00-\x1f]', '－', value).strip().rstrip('.')


def normalize_input(value):
    raw = value.replace('\\', '/')
    match = re.search(r'(?:^|/)ComfyUI/input/(.+)$', raw, re.I)
    if match:
        raw = match.group(1)
    path = PurePosixPath(raw)
    if path.is_absolute() or '..' in path.parts or ':' in raw:
        raise ValueError('Input path is outside the ComfyUI input directory')
    return path.as_posix()


def requirements(graph, definitions, runtime):
    missing_nodes = sorted({n['class_type'] for n in graph.values()} - set(definitions))
    models, assets, cached = [], [], []
    for key, node in graph.items():
        info = definitions.get(node['class_type'], {}).get('input', {})
        for field, value in node['inputs'].items():
            if field in MODEL_FIELDS and isinstance(value, str):
                schema = info.get('required', {}).get(field, info.get('optional', {}).get(field, []))
                choices = schema[0] if schema and isinstance(schema[0], list) else None
                models.append({'node': key, 'field': field, 'file': value,
                               'available': value in choices if choices is not None else None})
        if node['class_type'] == 'LoadImage':
            value = node['inputs']['image']
            relative = normalize_input(value)
            node['inputs']['image'] = relative
            source = ROOT / 'ComfyUI/input' / relative
            if not source.is_file():
                source = runtime / 'ComfyUI/input' / relative
            assets.append({'node': key, 'file': relative, 'source': source, 'exists': source.is_file(),
                           'original_value': value})
        if node['class_type'] == 'CLIPLoaderGGUF' and node['inputs'].get('clip_name') == 'Qwen-Image-2.1-Turbo-Uncensored-Q4_K.gguf':
            paired = 'mmproj-Qwen-Image-2.1-Turbo-Uncensored-F16.gguf'
            choices = info.get('required', {}).get('clip_name', [[]])[0]
            models.append({'node': key, 'field': 'automatic_mmproj', 'file': paired,
                           'available': paired in choices, 'autoloaded': True})
        if node['class_type'] in ARCHIVE_LOADERS:
            cached.append(node['inputs'].get('file', ''))
    return missing_nodes, models, assets, cached


def prepare(base='http://127.0.0.1:8188', install_inputs=True, snapshot=None):
    runtime = ROOT / 'runtime/ubuntu'
    if snapshot:
        definitions = json.loads(Path(snapshot).read_text())
        stats = {'system': {'argv': []}}
    else:
        with urlopen(base + '/object_info', timeout=30) as response:
            definitions = json.load(response)
        with urlopen(base + '/system_stats', timeout=10) as response:
            stats = json.load(response)
    LIBRARY.mkdir(exist_ok=True)
    TRIAL.mkdir(exist_ok=True)
    records, jobs, assets_manifest = [], [], {}
    previous_path = LIBRARY / 'catalog.json'
    previous = {j['id']: j for j in json.loads(previous_path.read_text())['workflows']} if previous_path.exists() else {}
    entries = catalog_records()
    phase_entries = []
    for record, _ in entries:
        for index, path in enumerate(record.get('phase_sources', [])):
            phase = copy.deepcopy(record)
            phase['phase'] = Path(path).parent.name.rsplit('--', 1)[-1]
            phase['phase_order'] = index + 1
            phase['record_id'] = record['id']
            phase['id'] += '--' + phase['phase']
            phase['case_id'] += '--' + phase['phase']
            phase['source'] = path
            phase['source_sha256'] = sha(ROOT / path)
            phase['title'] += f' / 阶段 {index + 1} ' + PHASE_LABELS[phase['phase']]
            executed_path = (ROOT / path).with_name('execution.json')
            if executed_path.exists():
                executed = json.loads(executed_path.read_text())
                command = executed.get('command', [])
                if '--extra-model-paths-config' in command:
                    phase['launch_args'] = command[command.index('--extra-model-paths-config') + 2:]
                    phase['launch_env'] = executed['environment']
                    phase['profile'] = f'阶段 {index + 1} {PHASE_LABELS[phase["phase"]]}实际配置：' + ' '.join(phase['launch_args']) + '；阶段完成后结束进程，再按下一阶段配置启动。'
            phase_entries.append((phase, json.loads((ROOT / path).read_text())))
            record.setdefault('phase_workflow_ids', []).append(phase['id'])
    for record, original_graph in entries + phase_entries:
        if not record.get('phase'):
            records.append(record)
        if not original_graph:
            record['workflow_reason'] = '缺少可追溯的完整计算图，未虚构可运行工作流'
            continue
        try:
            graph, changes = standalone_graph(original_graph, record['case_id'])
        except ValueError as error:
            record['workflow_reason'] = str(error)
            continue
        missing_nodes, models, assets, cached = requirements(graph, definitions, runtime)
        cache_dependencies = []
        if record.get('phase'):
            unresolved = []
            for filename in cached:
                source = (runtime / 'ComfyUI/input' / filename).resolve()
                expected = next(n['inputs'].get('expected_sha256') for n in graph.values() if n['class_type'] in ARCHIVE_LOADERS and n['inputs'].get('file') == filename)
                valid = source.is_relative_to((runtime / 'ComfyUI/input/repair_conditioning').resolve()) and source.is_file() and bool(expected) and sha(source) == expected
                cache_dependencies.append({'file': filename, 'sha256': expected, 'available': valid})
                if valid:
                    target = LIBRARY / 'input' / filename
                    target.parent.mkdir(parents=True, exist_ok=True)
                    if not target.exists(): shutil.copy2(source, target)
                    if sha(target) != expected: raise ValueError('Packaged conditioning changed')
                    assets_manifest[filename] = {'sha256': expected, 'bytes': source.stat().st_size, 'runtime_conflict': False, 'kind': 'conditioning_not_model_weights'}
                else: unresolved.append(filename)
            cached = unresolved
        missing_assets = []
        for asset in assets:
            if not asset['exists']:
                missing_assets.append(asset['file'])
                continue
            source = asset['source']
            digest = sha(source)
            # LoadImage's frontend choices list root files, not nested files.
            # Package a collision-resistant root name without touching originals.
            prefix = 'ModelLibrary_' + digest[:12] + '_'
            relative = source.name if source.name.startswith(prefix) else prefix + safe_name(source.name)
            asset['file'] = relative
            graph[asset['node']]['inputs']['image'] = relative
            if relative != asset['original_value']:
                changes.append('输入图片映射到 input 根目录；内容 SHA256 保持不变：' + asset['original_value'] + ' → ' + relative)
            target = LIBRARY / 'input' / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists() and sha(target) != digest:
                raise FileExistsError('Do not replace different packaged input: ' + relative)
            if not target.exists():
                shutil.copy2(source, target)
            installed = runtime / 'ComfyUI/input' / relative
            if install_inputs and not installed.exists():
                installed.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, installed)
            conflict = installed.exists() and sha(installed) != digest
            if conflict:
                missing_assets.append(relative + '（当前 input 存在不同内容，保留原件）')
            assets_manifest[relative] = {'sha256': digest, 'bytes': source.stat().st_size,
                                         'runtime_conflict': conflict}
        subpath = Path(safe_name(MODELS[record['model_id']])) / safe_name(FEATURES[record['feature_id']])
        stem = f"{record['platform']}__{record['case_id']}"
        if record.get('phase'):
            stem = f"Linux__{record['case_id'].rsplit('--', 1)[0]}__{record['phase_order']:02d}-" + PHASE_LABELS[record['phase']]
        elif record.get('staged_result'):
            stem += '__整图配方-未验收'
        api = LIBRARY / 'api' / subpath / (stem + '.api.json')
        ui = LIBRARY / 'ui' / subpath / (stem + '.json')
        api.parent.mkdir(parents=True, exist_ok=True)
        api_text = json.dumps(graph, ensure_ascii=False, indent=2) + '\n'
        if not api.exists() or api.read_text() != api_text:
            temporary = api.with_suffix('.' + str(os.getpid()) + '.tmp')
            temporary.write_text(api_text)
            temporary.replace(api)
        staged = bool(re.search('分阶段|进程分离|precompute|分离|阶段', record['profile'], re.I)) or bool(cached)
        metadata = {
            'id': record['id'], 'model_id': record['model_id'], 'feature_id': record['feature_id'],
            'record_id': record.get('record_id', record['id']), 'phase': record.get('phase'),
            'phase_order': record.get('phase_order'),
            'install_recommended': (record['platform'] == 'Windows' or record.get('launch_args') is None or
                                    (record['execution'] == 'success' and bool(record['images']) and record.get('image_healthy') and
                                     (bool(record.get('phase')) or not record.get('staged_result')))),
            'platform': record['platform'], 'case_id': record['case_id'],
            'launch_args': record.get('launch_args'), 'launch_env': record.get('launch_env', {}),
            'title': MODELS[record['model_id']] + ' / ' + FEATURES[record['feature_id']],
            'api': api.relative_to(ROOT).as_posix(), 'ui': ui.relative_to(ROOT).as_posix(),
            'source': record['source'], 'source_sha256': record['source_sha256'],
            'api_sha256': sha(api), 'transformations': changes,
            'missing_nodes': missing_nodes, 'models': models,
            'missing_models': [m['file'] for m in models if m['available'] is not True],
            'inputs': [{'node': a['node'], 'file': a['file'], 'available': a['exists'],
                        'original_value': a['original_value']} for a in assets],
            'missing_inputs': missing_assets, 'cached_archives': cached,
            'cache_dependencies': cache_dependencies,
            'staged_history': staged, 'staged_result': bool(record.get('staged_result')),
            'linux_output_available': record['platform'] == 'Linux' and bool(record['images']),
            'execution_verified_linux': record['platform'] == 'Linux' and record['execution'] == 'success' and bool(record['images']) and not record['blocked'] and not record.get('staged_result'),
            'required_profile': 'recorded' if record.get('launch_args') is not None
                                else 'qwen' if record['model_id'] == 'qwen-base' and record['platform'] == 'Linux'
                                else 'standard' if record['model_id'] == 'zimage-gguf' and record['platform'] == 'Linux'
                                else 'historical',
            'notes': '\n'.join(filter(None, [
                MODELS[record['model_id']] + ' / ' + FEATURES[record['feature_id']],
                '来源：' + record['platform'] + (' 实际尝试配方，执行/视觉状态见本例结论' if record.get('launch_args') is not None else ' 已执行配方' if record['platform'] == 'Linux' else ' 历史配方；未在当前 Linux 重跑'),
                '本例结论：' + str(record['verdict']),
                ('当前文件：阶段 1 反推。由 4B 视觉语言辅助模型生成描述并保存文本归档，记录路径和 SHA256。重启 CPU 编码配置后，在阶段 2 的 LoadRepairText 中更新二者；没有人工重写描述。' if record.get('phase') == 'caption' else
                 f'当前文件：阶段 {record.get("phase_order")} 编码。运行后记录条件归档路径与 SHA256，停止并重新启动服务，再打开下一阶段采样。修改提示词或输入后必须重新编码。' if record.get('phase') == 'encode' else
                 f'当前文件：阶段 {record.get("phase_order")} 采样。默认使用随包提供、经过 SHA256 校验的本例编码归档，可直接复现。若重新编码，请更新 LoadRepairConditioning 的 file 与 expected_sha256。' if record.get('phase') == 'sample' else
                 '注意：该条图片来自分阶段执行，本整图只作配方展示，直接整图尚未验收。' if record.get('staged_result') else ''),
                '配置：' + (record['profile'] or '历史启动参数未完整记录，不能承诺严格复现'),
                '本阶段启动参数：' + ' '.join(record['launch_args']) if record.get('phase') and record.get('launch_args') is not None else '',
                '完整启动命令：' + ' '.join(shlex.quote(k + '=' + str(v)) for k,v in record.get('launch_env', {}).items()) + ' bash scripts/start_ubuntu.sh --fast-disk ' + shlex.join(record['launch_args']) if record.get('launch_args') is not None else '',
                '输入：' + ('；'.join(a['file'] for a in assets) or '纯文本，无输入图片'),
                'UN GGUF 编码器需把 mmproj-Qwen-Image-2.1-Turbo-Uncensored-F16.gguf 放在编码器同目录，由加载器自动配对。' if any(m.get('autoloaded') for m in models) else '',
                '操作：先核对模型与输入，修改提示词，单次运行；seed 控制已设为 fixed。',
                '注意：历史结果来自分阶段/分进程执行；本整图只是配方整理，未验证直接连续运行。' if staged else '',
                '缺少节点：' + '、'.join(missing_nodes) if missing_nodes else '',
                '缺少模型：' + '、'.join(m['file'] for m in models if m['available'] is not True) if any(m['available'] is not True for m in models) else '',
            ])),
        }
        old = previous.get(metadata['id'], {})
        old_api = ROOT / old['api'] if old.get('api') else None
        if old_api and old_api != api and old_api.is_relative_to(LIBRARY / 'api') and old_api.is_file() and sha(old_api) == old.get('api_sha256'):
            old_api.unlink()
        if all(old.get(k) == metadata[k] for k in ('api_sha256', 'ui', 'notes', 'missing_nodes')) and (ROOT / metadata['ui']).is_file():
            if old.get('frontend_import'):
                metadata['frontend_import'] = old['frontend_import']
        record['workflow_id'] = metadata['id']
        jobs.append(metadata)
    # One family is still unconfirmed; do not substitute FLUX.2 for it.
    records.append({'id': 'pending-flux3-un', 'case_id': 'flux3-un-unconfirmed',
        'model_id': 'flux3-un', 'feature_id': 'unconfirmed', 'platform': 'Windows',
        'title': '准确权重与编码器配方未确认', 'verdict': '未验证', 'execution': '未执行',
        'review': '原交接保留待办；没有确认 Flux.3-5.6B-UN 的精确权重与四步配方，不使用 FLUX.2 Klein 的结果代替。',
        'blocked': True, 'images': [], 'profile': '', 'expected': '', 'prompt': '',
        'source': None, 'source_case_file': 'handoff.md', 'workflow_reason': '待明确准确模型与配方',
        'original_model_label': 'Flux.3-5.6B-UN', 'claim_level': '交接待办，非执行结果', 'original_case': {}})
    manifest = {'version': 1, 'models': MODELS, 'features': FEATURES, 'records': records,
                'workflows': jobs, 'input_assets': assets_manifest,
                'current_profile': 'coverage-in-progress' if snapshot else 'qwen' if '--force-fp16' in stats['system'].get('argv', []) else 'standard',
                'source_frontend_version': stats['system'].get('comfyui_frontend_version', '1.55.17'),
                'runtime_prefix': '模型功能库',
                'scope': 'UI import compatibility is checked separately from model execution; no Windows review is upgraded by a Linux graph import'}
    temporary = LIBRARY / ('catalog.' + str(os.getpid()) + '.tmp')
    temporary.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    temporary.replace(LIBRARY / 'catalog.json')
    used = {n['class_type'] for job in jobs for n in json.loads((ROOT / job['api']).read_text()).values()}
    selected_definitions = json.loads(json.dumps({k: definitions[k] for k in used if k in definitions}))
    actual_nodes = [n for job in jobs for n in json.loads((ROOT / job['api']).read_text()).values()]
    for kind, definition in selected_definitions.items():
        if kind == 'CLIPLoader': definition['description'] = '仅列出本工作流库实际使用的编码器配方。'
        for group in definition.get('input', {}).values():
            if not isinstance(group, dict): continue
            for field, spec in group.items():
                if spec and isinstance(spec[0], list):
                    values = [n['inputs'][field] for n in actual_nodes if n['class_type'] == kind and field in n['inputs']]
                    spec[0] = [choice for choice in spec[0] if choice in values]
    (TRIAL / 'node-definitions-used.json').write_text(json.dumps(selected_definitions, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'records': len(records), 'workflow_candidates': len(jobs), 'input_assets': len(assets_manifest),
                      'missing_node_cases': [j['case_id'] for j in jobs if j['missing_nodes']]}, ensure_ascii=False))
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', default='http://127.0.0.1:8188')
    parser.add_argument('--snapshot', type=Path, help='Previously live-verified node definitions, for progress reports while an isolated service owns the GPU')
    args = parser.parse_args()
    prepare(args.url, snapshot=args.snapshot)
