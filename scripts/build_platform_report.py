"""Render model → feature → Windows/Linux evidence without rewriting old reviews."""
import html
import json
import os
import shlex
from pathlib import Path
from urllib.parse import quote

from platform_catalog import ROOT, HERE, MODELS, FEATURES, sha
from report_evidence import comparison, ISSUE_FILE


def escape(value):
    return html.escape(str(value if value is not None else ''), quote=True)


def url(path):
    return quote(os.path.relpath(ROOT / path, HERE).replace(os.sep, '/'), safe='/._-')


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
        if job.get('staged_result') and job.get('linux_output_available'): return '分阶段已出图 · 整图未验收', 'partial'
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
        steps.append('先解决缺失节点 / 导入兼容问题；当前仅提供原 API 配方，不标为可直接运行。')
    steps.append('核对下列权重文件；不会自动下载或恢复已删除权重。输入图片按文件名对应到 LoadImage 节点，目标 / 参考顺序保持原图。')
    steps.append('修改提示词后单次运行。seed 的“生成后控制”已设 fixed；严格复现时保留下面的 seed、尺寸、采样器和步数。查看保存图片并对照本条原评价。')
    if job['staged_history']:
        steps.append('<strong>本条历史结果来自分阶段 / 分进程执行。</strong>整理后的整图只保留计算配方，不能把导入成功当作整图已在当前 Linux 跑通；原记录的执行边界仍适用。')
    models = ''.join(f'<li><code>{escape(m["file"])}</code><span class="chip {"good" if m["available"] is True else "bad"}">{"当前可见" if m["available"] is True else "未在当前服务找到"}</span></li>' for m in job['models'])
    inputs = ''.join(f'<li>节点 <code>{escape(a["node"])}</code> → <code>{escape(a["file"])}</code></li>' for a in job['inputs']) or '<li>纯文本，不需要输入图片。</li>'
    input_images = ''.join(f'<a href="{url("workflows/input/" + a["file"])}" target="_blank" rel="noopener"><img loading="lazy" src="{url("workflows/input/" + a["file"])}" alt="输入节点 {escape(a["node"])}：{escape(a["file"])}"></a>' for a in job['inputs'] if a['available'])
    params = '\n'.join(parameters(graph)) or '本例为后处理 / 合成，未记录采样参数。'
    actions = link(job['api'], 'API 配方')
    if job.get('frontend_import', {}).get('pass'):
        actions = link(job['ui'], '整图配方 · 未验收' if job.get('staged_result') else '下载 WebUI 工作流', True) + actions
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
    return ('<details class="timing"><summary>观测耗时 ' + seconds(data.get('reported_seconds'))
        + ' · 计时范围</summary><p>' + escape(data.get('scope', '原记录计时边界未完整采集'))
        + '</p><p>原生 history 执行区间：' + seconds(data.get('native_execution_seconds'))
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
    output = '<section class="feature-evidence"><details><summary>条件对照 · 功能可对照，性能不可比</summary><p>' + escape(data['reason']) + '</p><p class="muted">代表例 ' + escape(chosen) + '</p><div class="table-scroll"><table><thead><tr><th>条件</th><th>Windows</th><th>Linux</th><th>核对状态</th></tr></thead><tbody>' + rows + '</tbody></table></div><p>模型完整SHA、驱动/软件构建、存储、冷暖加载与计时阶段未全部统一。不同记录的秒数不计算平台加速倍数。</p></details>'
    registry = json.loads(ISSUE_FILE.read_text())
    ids = list(dict.fromkeys(i for r in by_platform['Linux'] for i in r.get('issue_ids', [])))
    for key in ids:
        issue = registry[key]
        affected = [r for r in by_platform['Linux'] if key in r.get('issue_ids', [])]
        output += '<details class="issue"><summary>Linux 问题：' + escape(issue['title']) + '</summary><p><strong>' + escape(issue['cause_status']) + '</strong></p>'
        for field, label in [('confirmed','已确认'),('unknown','尚未确认'),('attempts','已做尝试'),('solution','解决或规避方案'),('next','未完成工作')]:
            output += '<p><b>' + label + '：</b>' + escape(issue[field]) + '</p>'
        output += '<p>对应实测：' + '、'.join('<a href="#' + escape(r['id']) + '">' + escape(r['case_id']) + '</a>' for r in affected) + '</p></details>'
    if not by_platform['Linux']:
        output += '<p class="muted">Linux 尚未执行：准确权重与配方未确认，先确认来源和兼容节点，再提交实测；不将 Windows 成功自动记为 Linux 成功。</p>'
    elif not ids:
        output += '<p class="muted">本组没有新增未结案的 Linux 执行问题；目视结论仍以具体案例为准。</p>'
    return output + '</section>'


def record_html(record, job, phase_jobs=()):
    state, style = workflow_state(job)
    images = ''.join(f'<a href="{url(p)}" target="_blank" rel="noopener"><img loading="lazy" src="{url(p)}" alt="{escape(record["case_id"])} 输出"></a>' for p in record['images'])
    auxiliary = ''.join(f'<a href="{url(p)}" target="_blank" rel="noopener"><img loading="lazy" src="{url(p)}" alt="输入或遮罩预览，不计生成结果"></a>' for p in record.get('auxiliary_images', []))
    return (f'<details class="attempt" id="{escape(record["id"])}"><summary>'
            f'<span>{escape(record["title"])}</span><span class="chip {verdict_class(record["verdict"])}">{escape(record["verdict"])}</span></summary>'
            f'<p class="case-id">{escape(record["case_id"])} · 执行：{escape(record["execution"])}</p>'
            + timing_html(record) + ''
            f'<p class="literal">{escape(record["review"] or "未提供完整目视说明。")}</p>'
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
                '<span class="chip pending">未验证</span></div><p>尚无本平台、此模型与此功能的执行证据。</p>'
                '<p class="muted">另一平台的输出与导入检查均不会计作本平台通过。</p></section>')
    with_image = [r for r in records if r['images']]
    sample = with_image[-1] if with_image else records[-1]
    screenshots = [p for r in with_image[-2:] for p in r['images'][:1]] if platform == 'Linux' else sample['images'][:1]
    image_html = ''.join(f'<a href="{url(p)}" target="_blank" rel="noopener"><img loading="lazy" src="{url(p)}" alt="{platform} {escape(sample["title"])}"></a>' for p in screenshots)
    output = f'<div class="preview {"pair" if len(screenshots)>1 else ""}">{image_html}</div>' if image_html else '<div class="no-image">本组没有已收集的输出图片</div>'
    count = f'{len(records)} 条记录 · {len(with_image)} 条有图'
    sample_job = jobs.get(sample.get('workflow_id'))
    actions = ''
    if sample_job and sample_job.get('staged_result'):
        phase = next((jobs[k] for k in sample.get('phase_workflow_ids',[]) if k in jobs and jobs[k].get('phase') == 'sample'),None)
        if phase and phase.get('frontend_import',{}).get('pass'):
            actions = '<div class="actions">' + link(phase['ui'], '下载采样工作流 · 已备好归档', True) + '</div>'
    elif sample_job and sample_job.get('frontend_import', {}).get('pass'):
        actions = '<div class="actions">' + link(sample_job['ui'], '下载本例工作流', True) + '</div>'
    return (f'<section class="platform" data-platform="{platform}"><div class="platform-label"><span class="os-icon">{platform[0]}</span>'
            f'<h4>{platform}</h4><span class="record-count">{count}</span></div>'
            f'<span class="chip {verdict_class(sample["verdict"])}">{escape(sample["verdict"])}</span>'
            f'<p class="literal review-summary">{escape(sample["review"] or sample.get("expected", "尚无完整目视说明"))}</p>'
            + output + actions + '<p class="muted sample-note">上方为最近有图记录的代表例；下方保留本平台全部成功、部分达到及失败记录。</p>'
            + '<div class="attempt-list">' + ''.join(record_html(r, jobs.get(r.get('workflow_id')), [jobs[k] for k in r.get('phase_workflow_ids',[]) if k in jobs]) for r in reversed(records)) + '</div></section>')


def build_report():
    catalog = json.loads((ROOT / 'workflows/catalog.json').read_text())
    jobs = {j['id']: j for j in catalog['workflows']}
    records = catalog['records']
    model_html, nav, feature_count = [], [], 0
    for mid, title in MODELS.items():
        model_records = [r for r in records if r['model_id'] == mid]
        if not model_records: continue
        features = []
        for fid, feature in FEATURES.items():
            rows = [r for r in model_records if r['feature_id'] == fid]
            if not rows: continue
            feature_count += 1
            by_platform = {p: [r for r in rows if r['platform'] == p] for p in ('Windows', 'Linux')}
            has_linux = bool(by_platform['Linux'])
            linux_image = any(r['images'] for r in by_platform['Linux'])
            linux_met = any(r['images'] and r['execution'] == 'success' and verdict_class(r['verdict']) == 'good' for r in by_platform['Linux'])
            searchable = ' '.join([title, feature] + [r['case_id'] + ' ' + str(r['verdict']) for r in rows]).lower()
            feature_jobs = [jobs[r['workflow_id']] for r in rows if r.get('workflow_id') in jobs]
            importable = any(j.get('frontend_import', {}).get('pass') for j in feature_jobs)
            features.append(f'<article class="feature" id="{mid}--{fid}" data-search="{escape(searchable)}" data-linux="{str(has_linux).lower()}" data-linux-image="{str(linux_image).lower()}" data-linux-met="{str(linux_met).lower()}" data-workflow="{str(importable).lower()}">'
                f'<header class="feature-heading"><div><p class="eyebrow">{escape(title)}</p><h3>{escape(feature)}</h3></div>'
                f'<div class="feature-tags"><span class="chip {"good" if linux_image else "bad" if has_linux else "pending"}">{"两平台有图" if linux_image else "Linux 已尝试 · 暂无图" if has_linux else "Linux 待验证"}</span></div></header>'
                '<div class="platform-grid">' + ''.join(platform_panel(p, by_platform[p], jobs) for p in ('Windows', 'Linux')) + '</div>' + feature_evidence(by_platform) + '</article>')
        nav.append(f'<a class="model-link" href="#model-{mid}" data-model="{mid}"><span>{escape(title)}</span><small>{len(features)} 项功能</small></a>')
        model_html.append(f'<section class="model-section" id="model-{mid}" data-model="{mid}"><header class="model-heading"><h2>{escape(title)}</h2><span>{len(features)} 项功能 · {len(model_records)} 条证据</span></header>{"".join(features)}</section>')
    labels = {'linux-qwen-blue': '蓝眼提示预设', 'linux-qwen-green': '绿眼提示预设', 'linux-zimage-1': '红壶预设', 'linux-zimage-2': '蓝壶预设'}
    verified = []
    for mid, fid in [('qwen-turbo','t2i'),('zimage-aio','t2i'),('zimage-gguf','english-text'),('flux2','color')]:
        candidates = [r for r in records if r['platform'] == 'Linux' and r['model_id'] == mid and r['feature_id'] == fid and r['execution'] == 'success' and r['images'] and r.get('visual_inspected')]
        for record in reversed(candidates):
            job = jobs.get(record.get('workflow_id'))
            if job and job.get('staged_result'):
                job = next((jobs[k] for k in record.get('phase_workflow_ids',[]) if k in jobs and jobs[k].get('phase') == 'sample'),None)
            if job and job.get('frontend_import',{}).get('pass'):
                verified.append((job, record['title'], '迁移后的模型路径已实际出图。先按本例配置启动；分阶段的修改提示词步骤见下方详情。'))
                break
    for job in catalog['workflows']:
        if len(verified) >= 4: break
        if job['id'] in labels and job['execution_verified_linux'] and job.get('frontend_import',{}).get('pass'):
            verified.append((job, labels[job['id']], '历史 Linux 已出图配方，配置与执行边界见案例详情。'))
    quick = ''.join('<div class="quick-card"><span class="chip good">' + ('Linux 已出图 · 分阶段' if j.get('staged_result') else 'Linux 历史已出图') + '</span><h3>' + escape(MODELS[j['model_id']]) + ' · ' + escape(title) + '</h3><p>' + escape(note) + '</p>' + link(j['ui'], '下载采样工作流' if j.get('phase') == 'sample' else '下载 WebUI 工作流', True) + '</div>' for j,title,note in verified)
    template = (ROOT / 'scripts/platform_report_template.html').read_text()
    html_text = template.replace('@@NAV@@', ''.join(nav)).replace('@@MODELS@@', ''.join(model_html)).replace('@@QUICK@@', quick)
    replacements = {'@@MODEL_COUNT@@': str(len(model_html)), '@@FEATURE_COUNT@@': str(feature_count),
                    '@@RECORD_COUNT@@': str(len(records)), '@@UI_COUNT@@': str(sum(j.get('frontend_import', {}).get('pass', False) for j in catalog['workflows']))}
    for token, value in replacements.items(): html_text = html_text.replace(token, value)
    groups = {(r['model_id'], r['feature_id']) for r in records}
    linux_groups = {(r['model_id'], r['feature_id']) for r in records if r['platform'] == 'Linux'}
    image_groups = {(r['model_id'], r['feature_id']) for r in records if r['platform'] == 'Linux' and r['images']}
    coverage = f'Linux 功能进度：{len(image_groups)} / {len(groups)} 组已有输出图片；{len(linux_groups - image_groups)} 组已尝试但尚无图片；{len(groups - linux_groups)} 组尚未执行。图片与功能目视结论分别记录。'
    html_text = html_text.replace('@@COVERAGE@@', escape(coverage))
    bundle_status_path = ROOT / 'workflows/bundle-status.json'
    bundle_status = json.loads(bundle_status_path.read_text()) if bundle_status_path.exists() else {}
    synced = bundle_status.get('catalog_sha256') == sha(ROOT / 'workflows/catalog.json')
    html_text = html_text.replace('@@BUNDLE_STATUS@@', '下载包已同步本版工作流。完整包包含编码归档；轻量包需先编码并更新采样图中的归档路径与 SHA256。' if synced else '新结果持续追加中，下载包为最近一次完成前端检查的版本；单例下载以本页当前按钮为准，收尾时统一更新下载包。')
    distribution_file = ROOT / 'workflows/distribution.json'
    if distribution_file.is_file():
        for name, remote_url in json.loads(distribution_file.read_text()).get('assets', {}).items():
            html_text = html_text.replace('../../workflows/' + name, escape(remote_url))
    target = HERE / 'feature-report.html'
    temporary = HERE / ('feature-report.html.' + str(os.getpid()) + '.tmp')
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
