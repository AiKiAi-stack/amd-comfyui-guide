"""Register user-supplied offline article evidence without executing its scripts."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OFFLINE = Path('private-article-snapshot')  # Supply your own source folder; private original omitted.
pending_path = ROOT / 'research/pending-models.json'
pending = json.loads(pending_path.read_text(encoding='utf-8'))
records = []
for number, model, features in [
    ('01', 'Z-Image-Turbo-AIO FP8', ['文生图', '中英文文字渲染', '写实图像', '8步与4步效果比较']),
    ('02', 'jayn7/Z-Image-Turbo-GGUF Q4_K_M + unsloth/Qwen3-4B-GGUF Q4_K_M', ['文生图', '低显存量化运行', '修改提示词后输出变化']),
]:
    folder = next(p for p in OFFLINE.glob(number+'-*') if p.is_dir())
    metadata = json.loads((folder/'metadata.json').read_text(encoding='utf-8'))
    original = OFFLINE / (number+'-original.html')
    actual_sha = hashlib.sha256(original.read_bytes()).hexdigest()
    assert actual_sha == metadata['original_sha256']
    record = dict(title=metadata['title'], account=metadata['account'], publication_date=metadata['published'],
                  source_url=metadata['source_url'], model=model, features=features,
                  local_article=str(folder/'article.md'), local_original=str(original), original_sha256=actual_sha,
                  evidence='User supplied offline body and screenshots; no new WeChat network access.')
    records.append(record)
    item = next(p for p in pending if p['source_url'] == record['source_url'])
    item.update(record, status='source_verified_preparing_trial', trial_folder='trials/2026-10-20-zimage',
                source_access=record['evidence'], next_step='Verify exact public weights and author workflow, then local GPU inference.')
pending_path.write_text(json.dumps(pending, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
(HERE/'offline-article-evidence.json').write_text(json.dumps(records, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
audit = ROOT/'research/new-articles-2026-10-20.md'
marker = '## 用户提供的离线正文（新增证据）'
text = audit.read_text(encoding='utf-8')
if marker not in text:
    text += '\n'+marker+'\n\n先前的浏览器访问受阻记录仍然成立；以下来自用户明确提供的本地离线副本。没有重新请求微信原文。\n\n'
    for r in records:
        text += f"- {r['title']}；{r['account']}；{r['publication_date']}。模型：{r['model']}。正文路径：`{r['local_article']}`。原始 HTML SHA-256：`{r['original_sha256']}`。\n"
    text += '\nAIO 文中提到 NSFW，但重新打包或单文件布局本身不能证明经过特殊训练或能力增强；须独立核对模型卡，不能把所有社区模型都视为同一版本。10–40 秒、8GB、4步等均先记录为文章宣称。\n'
    audit.write_text(text, encoding='utf-8')
print(json.dumps(records, ensure_ascii=False, indent=2))
