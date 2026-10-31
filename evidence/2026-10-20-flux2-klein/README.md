# FLUX.2 Klein：七项编辑验收

更新于 2026-10-20T14:38:55.070084+00:00。设备 RX6650XT 8GB、16GB RAM；七项均有独立输入、prompt/workflow、history、PNG绑定校验与人工目视结论。

## Feature → output

- **单图编辑／改色（恢复锁页内存重试） — 通过**，提交后30.52秒。[输出](../report-assets/output/FeatureBench/flux2-klein-single-color-pinned_00001_.png) · [结果](cases/flux2-klein-single-color-pinned/result.json)。目视对照白包输入与实际输出：包身和提手均变为蓝色，保留居中手提包、皮革纹理和灰色摄影背景，包型及细节有小幅重绘，非像素保留。提交后30.52秒；恢复默认锁页内存后使用相同编辑图、权重和种子重试成功。旧禁用锁页配置的噪声图作为独立case保留；迭代编辑仅可使用本次已通过输出，derived_input哈希已与PNG一致。
- **双图编辑／配色与Logo迁移 — 通过**，提交后30.53秒。[输出](../report-assets/output/FeatureBench/flux2-klein-dual-logo_00001_.png) · [结果](cases/flux2-klein-dual-logo/result.json)。对照白色手提包和蓝底黄色Comfy图案两份输入，输出为蓝色皮革包，正面出现清楚黄色Comfy图案，包型、提手和灰背景保持。迁移图案有生成式细微变化，不宣称像素或矢量精确复制。 提交后30.53秒，未含服务冷启动；dynamic-nvme-pinned，参考约0.25MP。
- **双人合成／人物一致性 — 通过本例主要特征**，提交后36.74秒。[输出](../report-assets/output/FeatureBench/flux2-klein-dual-people_00001_.png) · [结果](cases/flux2-klein-dual-people/result.json)。恰好两名成年女性在阳光公园同框；左侧铜红卷发、雀斑和黄毛衣，右侧黑直发、蓝外套红围巾，人物属性未串换。与两张虚构参考图相比，脸型和表情有变化；本结论是目视特征保留，不是身份相似度量化。 提交后36.74秒，未含服务冷启动；dynamic-nvme-pinned，参考约0.25MP。
- **风格转换 — 部分达到／水彩清楚，光照改变**，提交后30.76秒。[输出](../report-assets/output/FeatureBench/flux2-klein-style_00001_.png) · [结果](cases/flux2-klein-style/result.json)。出现明确水彩晕染与冷压纸纹，猫背影、窗门、植物和街道构图大致保留；但原图深色雨夜与霓虹明显变浅，近似白昼光照，不能称严格保留原图环境。 提交后30.76秒，未含服务冷启动；dynamic-nvme-pinned，参考约0.25MP。
- **对象替换／中文指令 — 部分达到／替换生效，壶结构错误**，提交后25.66秒。[输出](../report-assets/output/FeatureBench/flux2-klein-replace-zh_00001_.png) · [结果](cases/flux2-klein-replace-zh/result.json)。中文指令已使白包消失，并在原灰色摄影背景中生成红色陶瓷壶状主体；但左右都像壶嘴，没有正常把手，茶壶结构明显错误。不能把对象替换API成功等同完整画质验收。 提交后25.66秒，未含服务冷启动；dynamic-nvme-pinned，参考约0.25MP。
- **对象删除 — 通过**，提交后25.9秒。[输出](../report-assets/output/FeatureBench/flux2-klein-remove_00001_.png) · [结果](cases/flux2-klein-remove/result.json)。猫被完整删除，没有可辨动物残留；原位置自然补成木质门廊/门板和植物，雨夜街道、咖啡窗和主要视角保留。细节发生重绘，没有遮罩节点或像素级背景保留保证。 提交后25.9秒，未含服务冷启动；dynamic-nvme-pinned，参考约0.25MP。
- **迭代编辑／第二轮修改 — 部分达到／添加生效，蝴蝶结偏大**，提交后25.32秒。[输出](../report-assets/output/FeatureBench/flux2-klein-iterative_00001_.png) · [结果](cases/flux2-klein-iterative/result.json)。已对照真正输入的上一轮蓝包输出：蓝色、包型、灰背景大致保持，左侧提手根部新增红色丝质蝴蝶结，确认第二轮图像编辑生效。蝴蝶结覆盖较大包面，不满足提示词small的小尺寸要求，因此只记部分达到。输入SHA与已目视通过的single-color-pinned输出一致，未使用首轮失败噪声图。提交后25.32秒，未含服务启动。

## 噪声诊断与运行边界

Two API-success outputs with disabled pinned memory were noise. Removing only that intended launch parameter in a new service restored T2I and all seven edits. This scopes a correctness issue to this local combination; low-level HIP/WDDM cause is not established.

两个噪声PNG与API成功记录均作为独立case保留；白包改蓝包成功重试没有覆盖失败图。迭代输入为已通过蓝包输出的同SHA副本，未使用失败图。

本机有效配置：G盘NVMe镜像、--enable-dynamic-vram、--fast-disk、默认锁页内存、--reserve-vram 2.0、--fp8_e4m3fn-text-enc、--cpu-vae、--disable-async-offload。此处不要加入--disable-pinned-memory；同参数AIO能工作不能外推Flux也正常。

Editing references use about 0.25 MP and preserve aspect ratio; output is not necessarily 512-square. No new 1024 test; historical 1024 native abort without output remains preserved. Timings exclude ComfyUI cold startup.

三份权重保留D盘原件，G盘副本SHA校验一致；各 `.ssd-verified.json` 及 `download-manifest.json` 记录确切版本。没有下载新版本权重或替代模型。

來源：[文章核对](../../docs/reference/research/new-articles-2026-10-20.md) · [固定工作流说明](workflows/recipe.md) · [逐项覆盖与资源记录](coverage.json)。工作流说明是准备阶段快照，实际执行/输入路径以case证据为准。

总图文报告：[feature-report.html](../../report/index.html)。
