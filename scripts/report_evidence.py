"""Describe measured timing, recipe differences and failure evidence without ranking OSes."""
import hashlib
import json
from pathlib import Path
import re
import struct

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / 'trials/2026-10-19-features'
ISSUE_FILE = ROOT / 'trials/2026-10-25-report-audit/linux-issues.json'


def read(path):
    return json.loads(path.read_text()) if path.is_file() else {}


def native_seconds(history):
    if not isinstance(history, dict): return None
    if 'status' not in history and len(history) == 1:
        history = next(iter(history.values()))
    status = history.get('status', {}) if isinstance(history, dict) else {}
    events = status.get('messages', []) if isinstance(status, dict) else []
    starts = [v['timestamp'] for k, v in events if k == 'execution_start' and 'timestamp' in v]
    ends = [v['timestamp'] for k, v in events if k in ('execution_success', 'execution_error') and 'timestamp' in v]
    return round((max(ends) - min(starts)) / 1000, 3) if starts and ends else None


def timing(record):
    folder = HERE / 'cases' / record['case_id']
    if record['platform'] == 'Linux' and record.get('launch_args') is not None:
        folder = ROOT / record['source_case_file']
        folder = folder.parent
        result = read(folder / 'execution.json')
        phases = []
        for source in record.get('phase_sources', []):
            phase = Path(source).parent
            item = read(ROOT / phase / 'execution.json')
            if not item: continue
            phases.append({'phase': phase.name.rsplit('--', 1)[-1],
                'observed_seconds': item.get('elapsed_seconds'), 'process_total_seconds': item.get('total_seconds'),
                'native_execution_seconds': native_seconds(read(ROOT / phase / 'history.json')),
                'source': (phase / 'execution.json').as_posix()})
        return {'scope': '已执行阶段提交后至结果收集的观测时间之和；不等于GPU纯采样时间',
                'reported_seconds': result.get('elapsed_seconds'), 'process_total_seconds': sum(p['process_total_seconds'] for p in phases) if phases and all(p['process_total_seconds'] is not None for p in phases) else result.get('total_seconds'),
                'native_execution_seconds': native_seconds(read(folder / 'history.json')) if not phases else None,
                'phases': phases, 'sampler_kernel_seconds': None,
                'includes': '模型读取/搬运、编码或采样、CPU解码及结果保存；进程总计另含启动/准备/清理',
                'cold_warm_controlled': False}
    result = read(folder / 'result.json')
    batch = result.get('batch_elapsed_seconds')
    return {'scope': result.get('elapsed_scope') or ('整批耗时，无法当作单案例耗时' if batch is not None and result.get('elapsed_seconds') is None else '历史案例提交至结果收集；编码/采样/解码未分别计时'),
            'reported_seconds': record.get('elapsed_seconds'), 'batch_seconds': batch,
            'native_execution_seconds': native_seconds(read(folder / 'history.json')),
            'process_total_seconds': None, 'phases': [], 'sampler_kernel_seconds': None,
            'includes': '包含模型加载/搬运和计算；历史记录未统一给出启动、缓存冷热及各阶段成本',
            'cold_warm_controlled': False}


def input_hash(value):
    value = value.replace('\\', '/')
    if 'ComfyUI/input/' in value: value = value.split('ComfyUI/input/', 1)[1]
    for root in (ROOT / 'ComfyUI/input', ROOT / 'runtime/ubuntu/ComfyUI/input'):
        path = root / value
        if path.is_file(): return hashlib.sha256(path.read_bytes()).hexdigest()
    return None


def recipe(record, graph):
    diffusion, encoders, prompts, inputs, sampling = [], [], [], [], []
    for node in graph.values():
        kind, values = node['class_type'], node['inputs']
        for key in ('unet_name', 'ckpt_name'):
            if key in values: diffusion.append(values[key])
        for key in ('clip_name', 'clip_name1', 'clip_name2'):
            if key in values: encoders.append(values[key])
        if kind == 'LoadImage': inputs.append(input_hash(values['image']))
        for key in ('text', 'prompt', 'negative_prompt'):
            if isinstance(values.get(key), str): prompts.append((kind, key, values[key]))
        selected = {k: v for k, v in values.items() if k in ('seed','noise_seed','steps','cfg','sampler_name','scheduler','denoise','sigmas','lora_name','strength_model','shift') and not isinstance(v, list)}
        if selected: sampling.append((kind, selected))
    args = record.get('encoding_launch_args', record.get('launch_args'))
    profile = record.get('profile', '')
    if args is not None:
        device = 'CPU' if '--cpu' in args else 'GPU自动选择（本轮执行日志为CUDA设备）'
        precision = 'BF16文本编码' if '--bf16-text-enc' in args else 'FP16全局/编码器按实际权重' if '--force-fp16' in args else '未显式统一文本计算精度'
        options = ' '.join(args)
    else:
        device = 'CPU（历史明确记录）' if re.search(r'编码器留在\s*CPU|CPU\s*(?:文字|文本)编码|文字.*?CPU', profile, re.I) else 'GPU（历史明确记录）' if re.search(r'GPU计算|GPU.*?编码|gpu-text', profile, re.I) else '历史未完整记录'
        precision = '见历史配置；未统一采集实际计算dtype'
        options = profile or '历史未完整记录'
    dimensions = None
    if record['images']:
        path = ROOT / record['images'][0]
        with path.open('rb') as f: header = f.read(24)
        if header[:8] == b'\x89PNG\r\n\x1a\n': dimensions = list(struct.unpack('>II', header[16:24]))
    return {'diffusion_files': sorted(diffusion), 'encoder_files': sorted(encoders),
            'input_sha256_ordered': inputs, 'prompt_sha256': hashlib.sha256(json.dumps(sorted(prompts), ensure_ascii=False).encode()).hexdigest(),
            'output_size': dimensions, 'sampling': sampling, 'text_device': device, 'precision': precision, 'runtime_options': options,
            'mode': str(len(record.get('phase_sources', []))) + '个独立进程阶段' if record.get('staged_result') else '历史多阶段记录，明细未统一' if re.search('分阶段|进程分离', profile) else '普通整图/历史单次案例',
            'model_hashes_cross_platform_verified': False, 'cold_warm_controlled': False}


def issue_ids(record):
    if record['platform'] != 'Linux' or record.get('launch_args') is None: return []
    result = read(ROOT / record['source_case_file'])
    cid, model, feature = record['case_id'], record['model_id'], record['feature_id']
    error = str(result.get('messages', [])) + str(result.get('error', ''))
    failed = result.get('status') != 'success'
    ids = []
    if failed:
        if 'Non-finite tensor' in error: ids.append('gpu-conditioning-nan')
        elif result.get('status') == 'operator_latency_stop': ids.append('caption-cpu-latency')
        elif result.get('status') == 'operator_ram_guard':
            ids.append('decode-memory' if '1024-gguf-te' in cid and result.get('failed_phase') != 'encoding' else 'host-memory-budget')
        elif model == 'kroma' and result.get('status') in ('operator_timeout', 'controller_error'): ids.append('model-switch-loading')
        else: ids.append('incomplete-execution')
    elif '部分' in record['verdict'] or '未达到' in record['verdict']:
        if feature in ('head','head-lora','face','pose','role'): ids.append('identity-details')
        elif model == 'moss' and feature == 'style': ids.append('moss-watercolor')
        elif feature == 'inpaint': ids.append('inpaint-species-seam')
        elif model == 'flux2' and feature in ('t2i','t2i-1024'): ids.append('extra-background-text')
        elif feature == 'iterative': ids.append('fine-size-control')
        else: ids.append('visual-goal-partial')
    return ids


def annotate(record, graph):
    record['timing'] = timing(record)
    record['recipe_conditions'] = recipe(record, graph)
    record['issue_ids'] = issue_ids(record)
    return record


def comparison(windows, linux):
    if not windows or not linux:
        return {'controlled': False, 'reason': '缺少一侧实测，不能作性能对照', 'differences': [], 'fields': []}
    a, b = windows.get('recipe_conditions', {}), linux.get('recipe_conditions', {})
    labels = [('diffusion_files','扩散模型文件'),('encoder_files','文本/视觉编码器'),('input_sha256_ordered','输入图片SHA与顺序'),('prompt_sha256','提示词SHA'),('output_size','输出尺寸'),('sampling','seed/步数/采样/LoRA'),('text_device','文本编码位置'),('precision','精度记录'),('mode','执行方式')]
    fields = []
    for key, label in labels:
        left, right = a.get(key), b.get(key)
        missing = left is None or right is None or (key == 'input_sha256_ordered' and (None in left or None in right))
        state = '未完整记录' if missing else '相同记录' if left == right else '不同'
        if key in ('diffusion_files','encoder_files') and state == '相同记录': state = '同文件名，跨平台SHA未逐项核对'
        fields.append({'key':key,'label':label,'windows':left,'linux':right,'state':state})
    return {'controlled': False, 'reason': '功能结果对照；配置、分阶段方式与冷暖加载未完成统一控制，禁止据此计算平台加速倍数',
            'differences':[f['label'] for f in fields if f['state']=='不同'], 'fields':fields}
