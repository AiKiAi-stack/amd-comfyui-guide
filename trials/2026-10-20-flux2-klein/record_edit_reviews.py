"""Record only edit outputs already inspected against their actual references."""
import json
from pathlib import Path
HERE=Path(__file__).resolve().parent
path=HERE/'reviews.json'
reviews=json.loads(path.read_text(encoding='utf-8'))
manual={
    'flux2-klein-dual-logo':('通过','对照白色手提包和蓝底黄色Comfy图案两份输入，输出为蓝色皮革包，正面出现清楚黄色Comfy图案，包型、提手和灰背景保持。迁移图案有生成式细微变化，不宣称像素或矢量精确复制。'),
    'flux2-klein-dual-people':('通过本例主要特征','恰好两名成年女性在阳光公园同框；左侧铜红卷发、雀斑和黄毛衣，右侧黑直发、蓝外套红围巾，人物属性未串换。与两张虚构参考图相比，脸型和表情有变化；本结论是目视特征保留，不是身份相似度量化。'),
    'flux2-klein-style':('部分达到／水彩清楚，光照改变','出现明确水彩晕染与冷压纸纹，猫背影、窗门、植物和街道构图大致保留；但原图深色雨夜与霓虹明显变浅，近似白昼光照，不能称严格保留原图环境。'),
    'flux2-klein-replace-zh':('部分达到／替换生效，壶结构错误','中文指令已使白包消失，并在原灰色摄影背景中生成红色陶瓷壶状主体；但左右都像壶嘴，没有正常把手，茶壶结构明显错误。不能把对象替换API成功等同完整画质验收。'),
    'flux2-klein-remove':('通过','猫被完整删除，没有可辨动物残留；原位置自然补成木质门廊/门板和植物，雨夜街道、咖啡窗和主要视角保留。细节发生重绘，没有遮罩节点或像素级背景保留保证。'),
}
for case_id,(verdict,notes) in manual.items():
    result=json.loads((HERE/'cases'/case_id/'result.json').read_text(encoding='utf-8'))
    assert result['status']=='success' and result['binding_validation']['passed']
    assert Path(result['images'][0]).is_file()
    reviews[case_id]=dict(verdict=verdict,notes=notes+f" 提交后{result['elapsed_seconds']}秒，未含服务冷启动；dynamic-nvme-pinned，参考约0.25MP。")
path.write_text(json.dumps(reviews,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('Saved five visual verdicts, including two partial feature results.')
