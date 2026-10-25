"""Platform evidence and standalone graph extraction; original trial files stay intact."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / 'trials/2026-10-19-features'
spec = importlib.util.spec_from_file_location('historical_report', HERE / 'build_report.py')
legacy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(legacy)

MODELS = {
    'qwen-base': 'Qwen-Image 2.1 · Base Q4_K_M',
    'qwen-turbo': 'Qwen-Image 2.1 Turbo · 普通 / UN 编码器',
    'kroma': 'Kroma v0.3.1 OPD · Q2_K',
    'moss': 'MOSS Image SFT · INT8',
    'flux2': 'FLUX.2 Klein 4B · FP8',
    'zimage-gguf': 'Z-Image Turbo · 双 GGUF Q4_K_M',
    'zimage-aio': 'Z-Image Turbo · FP8 AIO',
    'flux3-un': 'Flux.3-5.6B-UN · 配方待确认',
}
FEATURES = {
    't2i': '文生图与连续生成', 't2i-1024': '文生图 · 1024 分辨率',
    'english-text': '英文文字渲染', 'chinese-text': '中文文字渲染',
    'layout': '布局与位置描述', 'style': '图生图与风格转换',
    'style-reference': '风格参考 · 更换主体', 'multiref': '多图参考与主体合成',
    'head': '换头与人物身份参考', 'head-lora': 'BFS LoRA 专用换头', 'face': '仅面部身份替换',
    'inpaint': '遮罩局部重绘', 'role': '全身角色替换', 'pose': '姿态参考',
    'caption': '自动反推提示词并再生成', 'logo': '双图配色与 Logo 迁移',
    'people': '双人合成与人物一致性', 'replace': '对象替换 · 中文指令',
    'remove': '对象删除', 'color': '单图改色', 'iterative': '迭代编辑与蝴蝶结细节',
    'figure': '成年人体艺术探索', 'unconfirmed': '文生图 · 权重与配方待确认',
}


def read(path, fallback=None):
    return json.loads(path.read_text(encoding='utf-8-sig')) if path.is_file() else fallback


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def linked(value, graph):
    return (isinstance(value, list) and len(value) == 2 and isinstance(value[0], str)
            and value[0] in graph and isinstance(value[1], int))


def is_generated_image(filename, graph):
    """Runner filenames identify the output node; source/mask previews aren't renders."""
    root = Path(filename).stem.rsplit('-', 1)[0]
    seen = set()

    def visit(key):
        if key in seen or key not in graph: return False
        seen.add(key)
        node = graph[key]
        if node['class_type'] in ('KSampler', 'KSamplerAdvanced', 'SamplerCustomAdvanced', 'LoadRepairLatent'):
            return True
        return any(visit(value[0]) for value in node['inputs'].values() if linked(value, graph))

    return visit(root)


def standalone_graph(graph, case_id):
    """Extract one output, bypassing only the documented identity/wait barrier."""
    graph = copy.deepcopy(graph)
    changes = []
    barriers = {k: n['inputs']['conditioning'] for k, n in graph.items()
                if n['class_type'] == 'BenchmarkConditioningBarrier'}
    for node in graph.values():
        for key, value in list(node['inputs'].items()):
            if linked(value, graph) and value[0] in barriers:
                node['inputs'][key] = copy.deepcopy(barriers[value[0]])
                changes.append('去掉批量案例等待屏障，保持原 conditioning 连线')
    output_nodes = {k: n for k, n in graph.items()
                    if n['class_type'] in ('SaveImage', 'SaveAnimatedWEBP', 'SaveVideo', 'PreviewAny', 'SaveRepairConditioning', 'SaveRepairLatent', 'SaveRepairText')}
    roots = [k for k, n in output_nodes.items()
             if case_id in str(n['inputs'].get('filename_prefix', ''))]
    if not roots:
        roots = [k for k, n in output_nodes.items() if n['class_type'] != 'PreviewAny']
        if len(roots) != 1:
            generated = [k for k in roots if is_generated_image(k + '-0.png', graph)]
            if len(generated) != 1:
                raise ValueError(f'Cannot identify a single case output: {case_id}')
            roots = generated
            changes.append('变体保留原保存前缀时，按采样依赖抽取唯一生成结果，去掉输入/遮罩预览输出')
    wanted = set()

    def visit(key):
        if key in wanted:
            return
        wanted.add(key)
        for value in graph[key]['inputs'].values():
            if linked(value, graph):
                visit(value[0])

    for key in roots:
        visit(key)
    # Keep caption display when it only consumes an already required node.
    for key, node in output_nodes.items():
        if node['class_type'] == 'PreviewAny' and any(linked(v, graph) and v[0] in wanted for v in node['inputs'].values()):
            visit(key)
    if len(wanted) != len(graph):
        changes.append(f'从 {len(graph)} 个节点抽取本案例的 {len(wanted)} 个节点')
    return {k: n for k, n in graph.items() if k in wanted}, list(dict.fromkeys(changes))


def graph_source(case):
    folder = HERE / 'cases' / case['id']
    for name in ('original-workflow.api.json', 'workflow.api.json', 'api.json'):
        path = folder / name
        if path.is_file():
            return path
    path = legacy.legacy_api_path(case)
    if path:
        return path
    if case.get('workflow_api'):
        path = ROOT / 'trials/2026-10-20-zimage' / case['workflow_api']
        if path.is_file():
            return path
    return None


def model_id(case, graph):
    cid = case['id'].lower()
    weights = ' '.join(str(n['inputs'].get('unet_name', n['inputs'].get('ckpt_name', '')))
                       for n in graph.values() if n['class_type'] in
                       ('UnetLoaderGGUF', 'UnetLoaderGGUFDynamicVRAM', 'UNETLoader', 'CheckpointLoaderSimple')).lower()
    label = str(case.get('model', '')).lower()
    if 'z-image-turbo-fp8-aio' in weights or cid.startswith('zimage-aio'):
        return 'zimage-aio'
    if 'z_image_turbo' in weights or 'zimage' in cid or 'z-image' in label:
        return 'zimage-gguf'
    if 'kroma' in weights + label:
        return 'kroma'
    if 'moss' in weights + label:
        return 'moss'
    if 'flux' in weights + label or cid.startswith('flux2'):
        return 'flux2'
    if 'qwen-image-2.1-turbo' in weights or 'turbo' in label or cid.startswith('turbo-'):
        return 'qwen-turbo'
    return 'qwen-base'


def feature_id(case, model):
    cid = case['id'].lower()
    feature = case.get('feature', '')
    if case.get('recipe') == 't2i' and feature.startswith('文生图') and '1024' not in cid:
        return 't2i'
    if 'orange-to-white-cat' in cid:
        return 'color'
    if 'bfs' in cid:
        return 'head-lora'
    for marker, key in [('caption', 'caption'), ('face-only', 'face'), ('head', 'head'),
                        ('face-swap', 'head'), ('bfs', 'head'), ('role', 'role'),
                        ('pose', 'pose'), ('dual-logo', 'logo'), ('dual-people', 'people'),
                        ('multiref', 'multiref'), ('inpaint', 'inpaint'),
                        ('fox-', 'inpaint'), ('mask-fox', 'inpaint'),
                        ('chinese', 'chinese-text'), ('english', 'english-text'),
                        ('layout', 'layout'), ('figure-art', 'figure'),
                        ('tiny-bow', 'iterative'), ('iterative', 'iterative'),
                        ('replace-zh', 'replace'), ('teapot-structure', 'replace'), ('remove', 'remove')]:
        if marker in cid: return key
    if '风格参考' in feature: return 'style-reference'
    if case.get('recipe') == 't2i' and '素材' in feature: return 't2i'
    if 'style' in cid or 'watercolor' in cid or case.get('recipe') == 'img2img': return 'style'
    if cid == 'moss-text': return 'english-text'
    if '1024' in cid: return 't2i-1024'
    if 'single-color' in cid: return 'color'
    return 't2i'


def image_path(item, folder):
    if isinstance(item, dict) and item.get('file'):
        path = (folder / item['file']).resolve()
        if path.is_relative_to(ROOT) and path.is_file():
            return path
    return legacy.result_asset(item)


def evidence_record(case, record, platform, source, graph, blocked=False):
    model = model_id(case, graph)
    feature = feature_id(case, model)
    folder = source.parent if source else HERE / 'cases' / case['id']
    verdict, detail = legacy.review_for(case['id'], read(HERE / 'reviews.json', {}) if platform == 'Windows' else {}, record)
    if blocked:
        verdict, detail = legacy.review_for(case['id'], {}, case)
        detail = detail or case.get('reason', '')
    images = [p.relative_to(ROOT).as_posix() for item in (record or {}).get('images', [])
              if (p := image_path(item, folder))]
    return {'id': platform.lower() + '-' + case['id'], 'case_id': case['id'],
            'model_id': model, 'feature_id': feature, 'platform': platform,
            'title': case.get('feature', FEATURES[feature]), 'original_model_label': case.get('model', ''),
            'verdict': verdict, 'review': detail, 'execution': '未执行 / 阻塞' if blocked else str((record or {}).get('execution_status', (record or {}).get('status', '未记录'))),
            'blocked': blocked, 'images': images, 'elapsed_seconds': (record or {}).get('elapsed_seconds', (record or {}).get('elapsed')),
            'profile': case.get('runtime_profile', ''), 'expected': case.get('expected', ''),
            'prompt': case.get('prompt', ''), 'claim_level': case.get('claim_level', ''),
            'source': source.relative_to(ROOT).as_posix() if source else None,
            'source_sha256': sha(source) if source else None,
            'source_case_file': 'trials/2026-10-19-features/cases.json',
            'original_case': case}


def catalog_records():
    records = []
    for filename in ('baseline.json', 'cases.json', 'blocked.json'):
        for case in read(HERE / filename, []):
            source = graph_source(case)
            graph = read(source, {}) if source else {}
            result = read(HERE / 'cases' / case['id'] / 'result.json', None)
            if filename == 'baseline.json':
                result = {'images': case.get('images', []), 'review': case.get('review'),
                          'status': case.get('status', 'success'), 'elapsed_seconds': case.get('elapsed_seconds')}
            item = evidence_record(case, result, 'Windows', source, graph, filename == 'blocked.json')
            item['source_case_file'] = 'trials/2026-10-19-features/' + filename
            records.append((item, graph))
    zroot = ROOT / 'trials/2026-10-24-ubuntu'
    zsummary = read(zroot / 'zimage-repeat/summary.json')
    zreviews = read(zroot / 'zimage-reviews.json')['cases']
    for index, row in enumerate(zsummary['cases']):
        source = zroot / f'zimage-repeat/workflow-{index+1:02d}.json'
        graph = read(source)
        records.append(({'id': f'linux-zimage-{index+1}', 'case_id': f'zimage-linux-{index+1}',
            'platform': 'Linux', 'model_id': 'zimage-gguf', 'feature_id': 't2i',
            'title': '默认配置同进程红 / 蓝壶', 'original_model_label': 'Z-Image Turbo 双 GGUF',
            'verdict': '通过', 'review': zreviews[index]['review'], 'execution': 'success', 'blocked': False,
            'images': [(zroot / 'zimage-repeat' / i['file']).relative_to(ROOT).as_posix() for i in row['images']],
            'elapsed_seconds': row['seconds'], 'profile': '通用 Linux 入口 start_ubuntu.sh；CPU VAE；默认 pinned；已应用 Linux split attention 与 GGUF CPU-detach 补丁。两次提示 / 采样重跑；本记录未证明所有 reserved 显存释放。',
            'expected': '红/蓝茶壶与两颗柠檬，连续生成健康图片。', 'prompt': graph['8']['inputs']['text'],
            'claim_level': 'Linux 实际两轮输出 / history / 目视', 'source': source.relative_to(ROOT).as_posix(),
            'source_sha256': sha(source), 'source_case_file': 'trials/2026-10-24-ubuntu/zimage-reviews.json',
            'original_case': {}}, graph))
    qroot = ROOT / 'trials/2026-10-24-ubuntu-followup'
    accepted = read(qroot / 'acceptance.json')
    for color in ('blue', 'green'):
        source = qroot / f'qwen-ubuntu-{color}.api.json'
        result = read(qroot / f'direct-{color}/result.json')
        graph = read(source)
        records.append(({'id': f'linux-qwen-{color}', 'case_id': f'qwen-linux-{color}',
            'platform': 'Linux', 'model_id': 'qwen-base', 'feature_id': 't2i',
            'title': '纯文本普通整图 · 同进程连续生成', 'original_model_label': 'Base 扩散 + UN GGUF 编码器',
            'verdict': '执行通过 · 提示细节部分达到', 'review': result['review'],
            'execution': 'success', 'blocked': False, 'images': [(qroot / f'direct-{color}' / i['file']).relative_to(ROOT).as_posix() for i in result['images']],
            'elapsed_seconds': result['elapsed_seconds'], 'profile': 'Qwen Linux 专用入口 start_ubuntu_qwen.sh；FP16 + upcast / split attention；默认 pinned；CLIP CPU backing v4 + 延后 VAE。无参考图 / 无 LoRA。两次 /free active 通过，reserved 仍保留。',
            'expected': '完成 512×512、15步普通整图及同进程真实卸载。', 'prompt': graph['4']['inputs']['prompt'],
            'claim_level': 'Linux 独立 Python、无观察钩子、两轮完整出图；不是 Windows / Linux 同配方 A/B',
            'source': source.relative_to(ROOT).as_posix(), 'source_sha256': sha(source),
            'source_case_file': 'trials/2026-10-24-ubuntu-followup/acceptance.json',
            'minimum_available_ram_mib': accepted['minimum_observed_available_ram_mib'], 'original_case': {}}, graph))
    records.extend(coverage_records())
    from report_evidence import annotate
    return [(annotate(record, graph), graph) for record, graph in records]


def coverage_records():
    """Only append actual Ubuntu attempts; never infer execution from an import."""
    trial = ROOT / 'trials/2026-10-24-linux-coverage'
    records = []
    for case in read(trial / 'plan.json', []):
        folder = trial / 'cases' / case['case_id']
        result = read(folder / 'execution.json')
        if not result:
            continue
        source = ROOT / case['workflow']
        graph = read(source)
        if result.get('workflow_sha256') != sha(source):
            raise ValueError('Executed Linux workflow changed: ' + case['case_id'])
        command = result.get('command', [])
        actual_args = command[command.index('--extra-model-paths-config') + 2:] if '--extra-model-paths-config' in command else case['profile_args']
        encoding_command = result.get('encoding_command', command)
        encoding_args = encoding_command[encoding_command.index('--extra-model-paths-config') + 2:] if '--extra-model-paths-config' in encoding_command else actual_args
        review = read(folder / 'review.json', {})
        generated = [image for image in result['images'] if is_generated_image(image['file'], graph)]
        auxiliary = [image for image in result['images'] if not is_generated_image(image['file'], graph)]
        successful = result['status'] == 'success' and bool(generated) and not result.get('validation_errors')
        verdict = review.get('verdict', '已出图 · 待目视检查' if successful else '中止 · 无输出' if result['status'].startswith('operator_') else '失败 · 无输出')
        error = next((m[1] for m in result.get('messages', []) if m[0] == 'execution_error'), {})
        failure = result.get('error') or (' · '.join(str(error.get(k, '')).strip() for k in ('node_type','exception_type','exception_message')) if error else result['status'])
        detail = review.get('review', '已保存实际输出，尚未作功能目视验收。' if successful else str(failure))
        old = case['original_record']
        actual_prompts = '\n\n'.join(f'{node["class_type"]}.{field}:\n{value}'
            for node in graph.values() for field,value in node['inputs'].items()
            if field in ('prompt','text','negative_prompt') and isinstance(value,str))
        records.append(({'id': case['id'], 'case_id': case['case_id'], 'platform': 'Linux',
            'model_id': case['model_id'], 'feature_id': case['feature_id'],
            'title': old['title'] + ' · Ubuntu 实测', 'original_model_label': MODELS[case['model_id']],
            'verdict': verdict, 'review': detail, 'execution': result['status'], 'blocked': not successful,
            'visual_inspected': bool(review.get('visual_inspected')),
            'image_healthy': bool(review.get('image_healthy', review.get('visual_inspected') and '噪声' not in verdict and '破图' not in verdict)),
            'images': [(folder / image['file']).resolve().relative_to(ROOT).as_posix() for image in generated],
            'auxiliary_images': [(folder / image['file']).resolve().relative_to(ROOT).as_posix() for image in auxiliary],
            'elapsed_seconds': result['elapsed_seconds'], 'profile': ('Linux 分阶段/分进程，编码归档后结束进程，再采样；整图未验收；' if result.get('staged') else 'Linux 普通整图，独立进程；') + 'KEKE 只读权重；1536MiB 物理 RAM 保护；' + ' '.join(actual_args) + '；' + '；'.join(case['changes']),
            'launch_args': actual_args, 'launch_env': {'BARELY_COMFY_CHUNKED_CPU_LOGITS': '1', **result['environment']},
            'encoding_launch_args': encoding_args,
            'caption_text': result.get('caption_text'), 'three_phase_caption': case.get('execution_mode') == 'caption-three-phase',
            'staged_result': bool(result.get('staged')),
            'phase_sources': [(folder.parent / (case['case_id'] + '--' + phase) / 'workflow.api.json').relative_to(ROOT).as_posix() for phase in result.get('phase_names', ('encode','sample')) if (folder.parent / (case['case_id'] + '--' + phase) / 'workflow.api.json').is_file()] if result.get('staged') else [],
            'expected': old['expected'], 'prompt': actual_prompts or old['prompt'],
            'claim_level': 'Ubuntu 实际 history / 输出；Windows 历史评价未改；进程隔离不证明同进程卸载稳定性',
            'source': source.relative_to(ROOT).as_posix(), 'source_sha256': sha(source),
            'source_case_file': (folder / 'execution.json').relative_to(ROOT).as_posix(),
            'minimum_available_ram_mib': result['minimum_available_ram_mib'], 'original_case': {}}, graph))
    return records
