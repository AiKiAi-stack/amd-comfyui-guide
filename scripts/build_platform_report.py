"""Render model → feature → Windows/Linux evidence without rewriting old reviews."""
import html
import json
import os
import shlex
import struct
from functools import lru_cache
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import quote

from platform_catalog import ROOT, HERE, MODELS, FEATURES, sha
from report_evidence import comparison, ISSUE_FILE


OUT = ROOT / 'report'


PRESENTATION = ROOT / 'evidence/2026-10-26-report-edit'
TRIAL_NOTES = json.loads((PRESENTATION / 'trial-notes.json').read_text()) if (PRESENTATION / 'trial-notes.json').is_file() else {}
READING_SUMMARIES = json.loads((PRESENTATION / 'reading-summaries.json').read_text()) if (PRESENTATION / 'reading-summaries.json').is_file() else {}
MODEL_LABELS = {**MODELS, 'qwen-base':'Qwen-Image 2.1 Base', 'qwen-turbo':'Qwen-Image 2.1 Turbo', 'kroma':'Kroma 0.3.1 OPD', 'moss':'MOSS Image SFT', 'flux2':'FLUX.2 Klein 4B', 'zimage-gguf':'Z-Image Turbo · 双GGUF', 'zimage-aio':'Z-Image Turbo · FP8 AIO'}
FEATURE_LABELS = {**FEATURES, 't2i':'文生图', 't2i-1024':'1024文生图', 'style':'水彩风格转换', 'style-reference':'参考图风格', 'head':'换头', 'head-lora':'LoRA换头', 'face':'仅换脸', 'inpaint':'局部重绘', 'color':'图片改色', 'multiref':'多图合成', 'caption':'自动描述再生成', 'role':'全身人物替换', 'pose':'姿态参考', 'iterative':'小尺寸编辑', 'figure':'人体素描'}


def display_status(record):
    style = verdict_class(record.get('verdict', ''))
    if style == 'pending' or record.get('execution') in ('未执行','not_started'):
        return '未测试', 'pending'
    if not record.get('images'):
        return '未出图', 'bad'
    return {'good':('通过','good'), 'partial':('部分达到','partial'), 'bad':('未达到','bad')}.get(style, ('未测试','pending'))


def ordered_trials(records):
    if records and all(TRIAL_NOTES.get(r['id'], {}).get('order_unix_ms') is not None for r in records):
        return sorted(records, key=lambda r: TRIAL_NOTES[r['id']]['order_unix_ms'])
    return records


def reading_summary(record):
    key = record.get('model_id', '') + ':' + record.get('feature_id', '')
    return READING_SUMMARIES.get(key, {}).get(record.get('platform')) or record.get('review') or '尚无完整评价。'


def trial_story(record, index):
    note = TRIAL_NOTES.get(record['id'], {})
    stamp = note.get('order_unix_ms')
    date = datetime.fromtimestamp(stamp / 1000, timezone(timedelta(hours=8))).strftime('%m-%d %H:%M') if stamp else '未记录时间'
    label = note.get('label') or record['title']
    purpose = note.get('purpose') or ('首次测试本功能。' if index == 1 else '查看该次记录的目标与参数。')
    change = note.get('change') or '原始配置与提示词见本次参数。'
    outcome = note.get('result') or record.get('review') or '原记录未提供结果说明。'
    status, style = display_status(record)
    return ('<li class="trial-row"><div class="trial-heading"><strong>方案' + str(index) + ' · ' + escape(label)
        + '</strong><span class="chip ' + style + '">' + status + '</span></div><p class="muted">' + date
        + '</p><p><b>' + ('测试目的' if index == 1 else '为什么再测') + '：</b>' + escape(purpose)
        + '</p><p><b>本次改动：</b>' + escape(change) + '</p><p><b>结果：</b>' + escape(outcome) + '</p>')


def escape(value):
    return html.escape(str(value if value is not None else ''), quote=True)


def _repo_path(path):
    path = str(path).replace('\\', '/')
    name = path.rsplit('/', 1)[-1]
    if name in ('qwen-image-2.1-api.json', 'qwen-image-2.1-768-api.json'):
        return ROOT / 'evidence/report-assets/recipes' / name
    for prefix, target in (('ComfyUI/output/', 'evidence/report-assets/output/'),
                           ('ComfyUI/input/', 'evidence/report-assets/input/')):
        index = path.find(prefix)
        if index >= 0:
            return ROOT / (target + path[index + len(prefix):])
    if path.startswith('trials/'):
        path = 'evidence/' + path[len('trials/'):]
    return ROOT / path


def url(path):
    return quote(os.path.relpath(_repo_path(path), OUT).replace(os.sep, '/'), safe='/._-')


@lru_cache(maxsize=None)
def image_dimensions(path):
    file = _repo_path(path)
    if file.is_file():
        with file.open('rb') as stream: header = stream.read(24)
        if header[:8] == b'\x89PNG\r\n\x1a\n':
            width, height = struct.unpack('>II', header[16:24])
            return f'width="{width}" height="{height}"'
    return 'width="512" height="512"'


def link(path, label, download=False):
    return f'<a class="button {"primary" if download else ""}" href="{url(path)}" {"download" if download else ""}>{escape(label)}</a>'


def verdict_class(value):
    value = str(value).lower()
    if '部分' in value or 'partial' in value: return 'partial'
    if any(x in value for x in ('未验证', '尚未', 'pending', '未执行', '未记录')): return 'pending'
    if any(x in value for x in ('未达到', '未通过', '不通过', '未达标', '失败', '中止', 'blocked', 'crash', 'error')): return 'bad'
    if any(x in value for x in ('通过', '达到', '可用', 'pass')): return 'good'
    return 'pending'


def parameters(graph):
    items = []
    for node in graph.values():
        kind, inputs = node['class_type'], node['inputs']
        if kind in ('KSampler', 'KSamplerAdvanced', 'RandomNoise', 'EmptySD3LatentImage',
                    'EmptyLatentImage', 'EmptyFlux2LatentImage', 'ManualSigmas',
                    'Flux2Scheduler', 'LoraLoaderModelOnly', 'ModelSamplingAuraFlow',
                    'ModelSamplingSD3', 'CFGGuider', 'TextEncodeQwenImage21', 'TextGenerate', 'VAEDecodeTiled', 'ImageScale', 'ImageScaleToTotalPixels'):
            chosen = {k: v for k, v in inputs.items() if k in
                      ('seed', 'noise_seed', 'steps', 'cfg', 'sampler_name', 'scheduler', 'denoise',
                       'width', 'height', 'batch_size', 'sigmas', 'lora_name', 'strength_model', 'shift', 'resolution',
                       'tile_size', 'overlap', 'temporal_size', 'temporal_overlap', 'megapixels', 'upscale_method', 'crop',
                       'max_length', 'sampling_mode', 'thinking', 'mtp')}
            if chosen: items.append(kind + ' · ' + json.dumps(chosen, ensure_ascii=False))
    return items


def workflow_state(job):
    if not job: return '没有完整工作流', 'pending'
    if 'frontend_import' not in job: return '待前端检查', 'pending'
    if not job['frontend_import'].get('pass'): return '导入受阻', 'bad'
    if job['missing_models'] or job['missing_inputs']: return '缺少依赖', 'bad'
    if job['platform'] == 'Linux':
        if job.get('staged_result') and job.get('linux_output_available'): return '分步运行已出图；合并运行未测试', 'partial'
        return ('Linux 已出图', 'good') if job['execution_verified_linux'] else ('Linux 已尝试 · 未出图', 'bad')
    return 'Windows 历史配方 · Linux 结果见右侧独立记录', 'pending'


def reproduction(record, job, phase_jobs=()):
    if not job:
        return '<p class="muted">尚无可追溯的完整工作流：' + escape(record.get('workflow_reason', '配方待明确')) + '。不以其他模型的流程替代。</p>'
    graph = json.loads((ROOT / job['api']).read_text())
    profile = ('recorded' if job['required_profile'] == 'recorded'
               else 'bash scripts/start_ubuntu_qwen.sh' if job['required_profile'] == 'qwen'
               else 'bash scripts/start_ubuntu.sh' if job['required_profile'] == 'standard' else None)
    steps = []
    if profile:
        if record.get('launch_args') is not None:
            environment = ' '.join(shlex.quote(k + '=' + str(v)) for k,v in record.get('launch_env', {}).items())
            profile = environment + ' bash scripts/start_ubuntu.sh --fast-disk ' + shlex.join(record['launch_args'])
        steps.append('确认队列为空并停止原服务，再在仓库根用本例 Linux 配置启动：<code>' + escape(profile) + '</code>。')
    else:
        steps.append('按本条 Windows 历史记录的运行配置启动原环境。未完整记录的启动参数不补猜；本条不继承右侧 Linux 变体的执行结论。')
    if job.get('staged_result'):
        if record.get('three_phase_caption'):
            steps.append('<strong>本例是三个独立进程：</strong>① 4B 视觉语言模型反推并保存文本归档；② CPU/BF16 的 8B 编码器读取文本归档并保存条件；③ Base 扩散模型在 GPU 采样。每阶段完成后停止服务，再按下一阶段配置启动。')
            for phase in phase_jobs:
                command = ' '.join(shlex.quote(k + '=' + str(v)) for k,v in phase.get('launch_env', {}).items()) + ' bash scripts/start_ubuntu.sh --fast-disk ' + shlex.join(phase.get('launch_args') or [])
                steps.append('阶段 ' + str(phase['phase_order']) + ' ' + {'caption':'反推','encode':'编码','sample':'采样'}[phase['phase']] + '：<code>' + escape(command) + '</code>。')
            steps.append('新输入先运行反推阶段，将输出文本归档路径/SHA256 填入阶段 2 的 LoadRepairText；编码完成后再把条件归档路径/SHA256 填入阶段 3 的 LoadRepairConditioning。描述由模型直接传递，没有人工重写。保留原输入时，本机已有两份归档，可直接运行阶段 3。')
        elif record.get('encoding_launch_args') != record.get('launch_args'):
            encode_profile = environment + ' bash scripts/start_ubuntu.sh --fast-disk ' + shlex.join(record['encoding_launch_args'])
            steps.append('阶段 1 的编码设备配置与采样不同，编码时改用：<code>' + escape(encode_profile) + '</code>；编码结束后停止服务，阶段 2 再使用上方的采样配置。')
        if not record.get('three_phase_caption'):
            steps.append('<strong>本例分为编码与采样两个工作流。</strong>阶段 1 编码完成后记录输出归档路径与 SHA256，停止并按阶段 2 配置重启 ComfyUI；再打开阶段 2 采样，将归档路径与 SHA256 填入 LoadRepairConditioning。默认已指向随包提供、本机已有的本例归档，保留原输入时可直接运行阶段 2。')
        steps.append('更换提示词、参考图或顺序后必须重跑阶段 1 并更新阶段 2 的归档字段。整图 JSON 只展示原计算配方，不能代替上述分进程步骤。归档在完整下载包的 input/repair_conditioning 下，复制到 ComfyUI/input/repair_conditioning。')
    elif job.get('frontend_import', {}).get('pass'):
        location = '模型功能库 / ' + ' / '.join(Path(job['ui']).parts[2:-1])
        if job.get('install_recommended', True):
            steps.append('在 WebUI 左侧“工作流”中打开 <strong>' + escape(location) + '</strong>，选择文件 <code>' + escape(Path(job['ui']).name) + '</code>。也可下载下方 UI JSON 后通过“打开工作流”载入。')
        else:
            steps.append('本条尚无健康执行输出，未安装到本机推荐库。需要复查原失败时，可下载下方 UI JSON 后通过“打开工作流”载入，并按原停止边界操作。')
    else:
        steps.append('先解决缺失节点 / 导入兼容问题；当前仅提供原 API文件，不标为可直接运行。')
    steps.append('核对下列权重文件；不会自动下载或恢复已删除权重。输入图片按文件名对应到 LoadImage 节点，目标 / 参考顺序保持原图。')
    steps.append('修改提示词后单次运行。seed 的“生成后控制”已设 fixed；严格复现时保留下面的 seed、尺寸、采样器和步数。查看保存图片并对照本条原评价。')
    if job['staged_history']:
        steps.append('<strong>本条历史结果来自分阶段 / 分进程执行。</strong>整理后的整图只保留计算配方，不能把导入成功当作整图已在当前 Linux 跑通；原记录的执行边界仍适用。')
    models = ''.join(f'<li><code>{escape(m["file"])}</code><span class="chip {"good" if m["available"] is True else "bad"}">{"当前可见" if m["available"] is True else "未在当前服务找到"}</span></li>' for m in job['models'])
    inputs = ''.join(f'<li>节点 <code>{escape(a["node"])}</code> → <code>{escape(a["file"])}</code></li>' for a in job['inputs']) or '<li>纯文本，不需要输入图片。</li>'
    input_images = ''.join(f'<a href="{url("workflows/input/" + a["file"])}" target="_blank" rel="noopener"><img {image_dimensions("workflows/input/" + a["file"])} loading="lazy" src="{url("workflows/input/" + a["file"])}" alt="输入节点 {escape(a["node"])}：{escape(a["file"])}"></a>' for a in job['inputs'] if a['available'])
    params = '\n'.join(parameters(graph)) or '本例为后处理 / 合成，未记录采样参数。'
    actions = link(job['api'], 'API文件')
    if job.get('frontend_import', {}).get('pass'):
        actions = link(job['ui'], '合并工作流（未运行）' if job.get('staged_result') else '下载 WebUI 工作流', True) + actions
    phase_actions = ''
    for phase in phase_jobs:
        if phase and phase.get('frontend_import', {}).get('pass'):
            phase_actions += link(phase['ui'], str(phase.get('phase_order', '')) + ' · ' + {'caption':'反推','encode':'编码','sample':'采样'}[phase['phase']] + '工作流', True)
    actions = phase_actions + actions
    if job.get('source'): actions += link(job['source'], '原始执行图')
    return ('<ol>' + ''.join('<li>' + s + '</li>' for s in steps) + '</ol>'
            + '<div class="recipe-columns"><div><h5>模型文件</h5><ul class="files">' + models + '</ul></div>'
            + '<div><h5>输入图片</h5><ul class="files">' + inputs + '</ul><div class="result-images">' + input_images + '</div></div></div>'
            + '<h5>运行配置原文</h5><p class="literal">' + escape(record.get('profile') or '原记录未完整记录启动参数。') + '</p>'
            + '<h5>关键节点参数</h5><pre>' + escape(params) + '</pre><div class="actions">' + actions + '</div>')


def seconds(value):
    return f'{value:.2f} 秒' if isinstance(value, (float, int)) else '未记录'


def timing_html(record):
    data = record.get('timing', {})
    phases = ''.join('<li>' + escape(p['phase']) + '：观测 ' + seconds(p.get('observed_seconds'))
        + '；进程总计 ' + seconds(p.get('process_total_seconds')) + '</li>' for p in data.get('phases', []))
    return ('<details class="timing"><summary>本次耗时 ' + seconds(data.get('reported_seconds'))
        + ' · 计时范围</summary><p>' + escape(data.get('scope', '原记录计时边界未完整采集'))
        + '</p><p>ComfyUI记录的执行时间：' + seconds(data.get('native_execution_seconds'))
        + '；进程总计：' + seconds(data.get('process_total_seconds'))
        + ('；整批观测：' + seconds(data['batch_seconds']) if data.get('batch_seconds') is not None else '')
        + '</p><ul>' + phases + '</ul><p class="muted">GPU纯采样时间未单独记录。'
        + escape(data.get('includes', '加载、编码、采样、解码尚未分别计时。')) + '</p></details>')


def representative(records):
    with_image = [r for r in records if r['images']]
    return (with_image or records)[-1] if records else None


def feature_evidence(by_platform):
    selected = {p: representative(by_platform[p]) for p in ('Windows', 'Linux')}
    data = comparison(selected['Windows'], selected['Linux'])
    def value(v):
        return escape(json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else v if v is not None else '未记录')
    rows = ''.join('<tr><th>' + escape(f['label']) + '</th><td>' + value(f['windows']) + '</td><td>'
        + value(f['linux']) + '</td><td>' + escape(f['state']) + '</td></tr>' for f in data['fields'])
    chosen = '；'.join(p + '：' + r['case_id'] for p,r in selected.items() if r)
    output = '<section class="feature-evidence"><details><summary>两平台使用的配置</summary><p>' + escape('缺少一侧的运行结果。' if not selected['Windows'] or not selected['Linux'] else '运行配置存在差异，这些耗时不能用于比较系统速度。') + '</p><p class="muted">代表例 ' + escape(chosen) + '</p><div class="table-scroll"><table><thead><tr><th>条件</th><th>Windows</th><th>Linux</th><th>核对状态</th></tr></thead><tbody>' + rows + '</tbody></table></div><p>模型完整SHA、驱动/软件构建、存储、冷暖加载与计时阶段未全部统一。不同记录的秒数不计算平台加速倍数。</p></details>'
    registry = json.loads(ISSUE_FILE.read_text())
    ids = list(dict.fromkeys(i for r in by_platform['Linux'] for i in r.get('issue_ids', [])))
    for key in ids:
        issue = registry[key]
        affected = [r for r in by_platform['Linux'] if key in r.get('issue_ids', [])]
        output += '<details class="issue"><summary>Linux问题：' + escape(issue['title']) + '</summary><p><strong>' + escape(issue['cause_status']) + '</strong></p>'
        for field, label in [('confirmed','已确认'),('unknown','尚未确认'),('attempts','已做尝试'),('solution','解决或规避方案'),('next','未完成工作')]:
            output += '<p><b>' + label + '：</b>' + escape(issue[field]) + '</p>'
        output += '<p>查看相关记录：' + '、'.join('<a href="#' + escape(r['id']) + '">' + escape(r['case_id']) + '</a>' for r in affected) + '</p></details>'
    if not by_platform['Linux']:
        output += '<p class="muted">尚无本平台的运行记录。</p>'
    elif not ids:
        output += '<p class="muted">本组没有新增运行问题；图像效果见上方结果。</p>'
    return '<details class="technical-details"><summary>配置差异与问题排查</summary>' + output + '</section></details>'


def record_html(record, job, phase_jobs=()):
    state, style = workflow_state(job)
    status_label, status_style = display_status(record)
    images = ''.join(f'<a href="{url(p)}" target="_blank" rel="noopener"><img {image_dimensions(p)} loading="lazy" src="{url(p)}" alt="{escape(record["case_id"])} 输出"></a>' for p in record['images'])
    auxiliary = ''.join(f'<a href="{url(p)}" target="_blank" rel="noopener"><img {image_dimensions(p)} loading="lazy" src="{url(p)}" alt="输入或遮罩预览，不计生成结果"></a>' for p in record.get('auxiliary_images', []))
    return (f'<details class="attempt" id="{escape(record["id"])}"><summary>'
            f'<span>{escape(record["title"])}</span><span class="chip {status_style}">{status_label}</span></summary>'
            f'<p class="case-id">{escape(record["case_id"])} · 执行：{escape(record["execution"])}</p>'
            + timing_html(record) + ''
            f'<p class="muted">原评价用语：{escape(record["verdict"])}</p><p class="literal">{escape(record["review"] or "未提供完整目视说明。")}</p>'
            + ('<details><summary>模型自动生成的描述 · 原文</summary><pre>' + escape(record['caption_text']) + '</pre></details>' if record.get('caption_text') else '')
            + f'<p class="muted">原模型标签：{escape(record.get("original_model_label", ""))} · 来源：{escape(record.get("claim_level", ""))}</p>'
            f'<div class="result-images">{images}</div><span class="chip {style}">{escape(state)}</span>'
            + ('<details><summary>输入与遮罩预览 · 不计生成结果</summary><div class="result-images">' + auxiliary + '</div></details>' if auxiliary else '')
            + '<details class="reproduce"><summary>复现步骤、模型、输入与工作流</summary>' + reproduction(record, job, phase_jobs) + '</details>'
            '<details class="prompt"><summary>完整提示词与原预期</summary><pre>' + escape(record.get('prompt', '')) + '</pre><p>' + escape(record.get('expected', '')) + '</p></details>'
            + (link(record['source_case_file'], '原始结果 / 来源索引') if record.get('source_case_file') else '') + '</details>')


def platform_panel(platform, records, jobs):
    if not records:
        return (f'<section class="platform empty" data-platform="{platform}"><div class="platform-label"><span class="os-icon">{platform[0]}</span><h4>{platform}</h4>'
                '<span class="chip pending">未测试</span></div><p>尚无本平台的运行记录。</p>'
                '</section>')
    records = ordered_trials(records)
    sample = representative(records)
    label, style = display_status(sample)
    image_html = ''.join(f'<a href="{url(p)}" target="_blank" rel="noopener"><img {image_dimensions(p)} loading="lazy" src="{url(p)}" alt="{platform} {escape(FEATURE_LABELS.get(sample.get("feature_id"),sample["title"]))}输出"></a>' for p in sample['images'][:1])
    output = '<div class="preview">' + image_html + '</div>' if image_html else '<div class="no-image">尚无输出图片</div>'
    job = jobs.get(sample.get('workflow_id'))
    phase_jobs = [jobs[k] for k in sample.get('phase_workflow_ids', []) if k in jobs]
    sample_job = next((j for j in phase_jobs if j.get('phase') == 'sample'), job)
    actions = ''
    if sample_job and sample_job.get('frontend_import', {}).get('pass'):
        actions = '<div class="actions">' + link(sample_job['ui'], '下载出图工作流' if sample.get('staged_result') else '下载工作流', True) + '</div>'
    history = ''
    if platform == 'Linux':
        timed = all(TRIAL_NOTES.get(r['id'], {}).get('order_unix_ms') is not None for r in records)
        order_note = '按先后排列，时间为北京时间' if timed else '按原方案登记顺序；旧记录缺少完整时间'
        history = '<details class="test-history"><summary>测试过程 · ' + str(len(records)) + '个方案</summary><p class="muted">' + order_note + '。每个方案列出改动和结果。</p><ol class="trial-list">'
        for index, record in enumerate(records, 1):
            history += trial_story(record, index) + record_html(record, jobs.get(record.get('workflow_id')), [jobs[k] for k in record.get('phase_workflow_ids',[]) if k in jobs]) + '</li>'
        history += '</ol></details>'
    else:
        history = '<details class="test-history"><summary>Windows原始记录 · ' + str(len(records)) + '条</summary><div class="attempt-list">' + ''.join(record_html(r, jobs.get(r.get('workflow_id')), [jobs[k] for k in r.get('phase_workflow_ids',[]) if k in jobs]) for r in records) + '</div></details>'
    launch = ''
    if platform == 'Linux' and sample.get('staged_result'):
        device = 'CPU编码，再用GPU出图' if '--cpu' in sample.get('encoding_launch_args',[]) else '编码完成后重启服务，再用GPU出图'
        if sample.get('three_phase_caption'): device = '4B模型生成描述，8B在CPU编码，再用GPU出图'
        launch = '<p class="run-method">运行方法：' + device + '。</p>'
    repro = '<details class="reproduce current-reproduction"><summary>使用步骤与完整参数</summary>' + reproduction(sample, job, phase_jobs) + '</details>' if job else ''
    return (f'<section class="platform" data-platform="{platform}"><div class="platform-label"><span class="os-icon">{platform[0]}</span>'
        f'<h4>{platform}</h4><span class="chip {style}">{label}</span></div><p class="current-result">' + escape(reading_summary(sample)) + '</p>'
        + output + launch + actions + repro + history + '</section>')


def build_report():
    catalog = json.loads((ROOT / 'workflows/catalog.json').read_text())
    jobs = {j['id']: j for j in catalog['workflows']}
    records = catalog['records']
    model_html, nav, feature_count = [], [], 0
    for mid, original_title in MODELS.items():
        title = MODEL_LABELS[mid]
        model_records = [r for r in records if r['model_id'] == mid]
        if not model_records: continue
        features = []
        for fid, original_feature in FEATURES.items():
            feature = FEATURE_LABELS[fid]
            rows = [r for r in model_records if r['feature_id'] == fid]
            if not rows: continue
            feature_count += 1
            by_platform = {p: [r for r in rows if r['platform'] == p] for p in ('Windows', 'Linux')}
            has_linux = bool(by_platform['Linux'])
            linux_image = any(r['images'] for r in by_platform['Linux'])
            linux_met = any(r['images'] and r['execution'] == 'success' and verdict_class(r['verdict']) == 'good' for r in by_platform['Linux'])
            current_linux = representative(ordered_trials(by_platform['Linux']))
            linux_status = display_status(current_linux)[0] if current_linux else '未测试'
            searchable = ' '.join([title, feature] + [r['case_id'] + ' ' + str(r['verdict']) for r in rows]).lower()
            feature_jobs = [jobs[r['workflow_id']] for r in rows if r.get('workflow_id') in jobs]
            importable = any(j.get('frontend_import', {}).get('pass') for j in feature_jobs)
            features.append(f'<article class="feature" id="{mid}--{fid}" data-search="{escape(searchable)}" data-linux-status="{linux_status}" data-linux="{str(has_linux).lower()}" data-linux-image="{str(linux_image).lower()}" data-linux-met="{str(linux_met).lower()}" data-workflow="{str(importable).lower()}">'
                f'<header class="feature-heading"><div><p class="eyebrow">{escape(title)}</p><h3>{escape(feature)}</h3></div>'
                f'<div class="feature-tags"><span class="chip {"good" if linux_image else "bad" if has_linux else "pending"}">{"两平台有图" if linux_image else "Linux 未出图" if has_linux else "Linux 未测试"}</span></div></header>'
                '<div class="platform-grid">' + ''.join(platform_panel(p, by_platform[p], jobs) for p in ('Windows', 'Linux')) + '</div>' + feature_evidence(by_platform) + '</article>')
        nav.append(f'<a class="model-link" href="#model-{mid}" data-model="{mid}"><span>{escape(title)}</span><small>{len(features)} 项功能</small></a>')
        model_html.append(f'<section class="model-section" id="model-{mid}" data-model="{mid}"><header class="model-heading"><h2>{escape(title)}</h2><span>{len(features)} 项功能</span></header>{"".join(features)}</section>')
    template = (ROOT / 'scripts/platform_report_template.html').read_text()
    html_text = template.replace('@@NAV@@', ''.join(nav)).replace('@@MODELS@@', ''.join(model_html))
    replacements = {'@@MODEL_COUNT@@': str(len(model_html)), '@@FEATURE_COUNT@@': str(feature_count),
                    '@@RECORD_COUNT@@': str(len(records)), '@@UI_COUNT@@': str(sum(j.get('frontend_import', {}).get('pass', False) for j in catalog['workflows']))}
    for token, value in replacements.items(): html_text = html_text.replace(token, value)
    linux_outcomes = [display_status(representative(ordered_trials([r for r in records if r['platform'] == 'Linux' and (r['model_id'],r['feature_id']) == pair])))[0]
        for pair in sorted({(r['model_id'],r['feature_id']) for r in records if r['platform'] == 'Linux'})]
    coverage = 'Linux：' + '，'.join(f'{linux_outcomes.count(status)}项{status}' for status in ('通过','部分达到','未达到')) + '。'
    html_text = html_text.replace('@@COVERAGE@@', escape(coverage))
    bundle_status_path = ROOT / 'workflows/bundle-status.json'
    bundle_status = json.loads(bundle_status_path.read_text()) if bundle_status_path.exists() else {}
    synced = bundle_status.get('catalog_sha256') == sha(ROOT / 'workflows/catalog.json')
    html_text = html_text.replace('@@BUNDLE_STATUS@@', '下载包已同步本版工作流。完整包包含编码归档；轻量包需先编码并更新采样图中的归档路径与 SHA256。' if synced else '新结果持续追加中，下载包为最近一次完成前端检查的版本；单例下载以本页当前按钮为准，收尾时统一更新下载包。')
    distribution_file = ROOT / 'workflows/distribution.json'
    if distribution_file.is_file():
        for name, remote_url in json.loads(distribution_file.read_text()).get('assets', {}).items():
            html_text = html_text.replace('../../workflows/' + name, escape(remote_url))
    OUT.mkdir(parents=True, exist_ok=True)
    target = OUT / 'index.html'
    temporary = OUT / ('index.html.' + str(os.getpid()) + '.tmp')
    temporary.write_text(html_text, encoding='utf-8')
    temporary.replace(target)
    matrix = {'models': MODELS, 'features': FEATURES, 'records': records,
              'legacy_record_count': 95, 'scope': '按功能对照，不是同提示/seed/精度的跨平台速度基准；导入不等于执行'}
    temporary = HERE / ('platform-comparison.json.' + str(os.getpid()) + '.tmp')
    temporary.write_text(json.dumps(matrix, ensure_ascii=False, indent=2) + '\n')
    temporary.replace(HERE / 'platform-comparison.json')
    print(json.dumps({'html': str(target), 'models': len(model_html), 'features': feature_count,
                      'records': len(records), 'ui_workflows': replacements['@@UI_COUNT@@']}, ensure_ascii=False))
    return target


if __name__ == '__main__':
    build_report()
