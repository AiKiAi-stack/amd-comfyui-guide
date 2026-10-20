# 用户新增三篇模型文章

## 1. 已读取正文

- 链接：https://mp.weixin.qq.com/s/XNsQ6n0wxZmbgpZl747CMQ
- 标题：Flux.2 Klein 本地安装攻略和一键包!
- 公众号：托尼不是塔克；作者显示 Tony。
- 页面发布时间：2026-01-21 23:57，浙江。
- 模型：FLUX.2 Klein 4B **蒸馏版**。文章使用 ComfyUI 官方模板，展示单图编辑、手提包与 Logo 的双图配色/Logo迁移、双人合成；正文也提到样式转换、对象替换/删除和迭代编辑。
- 作者一键包获取方式：向该公众号发送 `Flux2Klein`。本次没有发送消息，正文没有直接给出网盘地址。
- 首次正文读取：浏览器正常返回完整可读文章；随后同域的另一链接被浏览器站点安全策略拒绝，本次不再尝试微信访问。

## 2. 正文未读取

- 链接：https://mp.weixin.qq.com/s/b-JAe4AbZCc5SDCcutRU_Q
- 浏览器站点安全策略拒绝访问。标题、日期、模型和下载链接均未知；已请用户补充。

## 3. 正文未读取

- 链接：https://mp.weixin.qq.com/s/ads74_hTHki3Kft18je04Q
- 与第二篇一起进入访问尝试后，浏览器在同域安全检查时拒绝继续。没有取得第三篇正文；标题、日期、模型和下载链接均未知，已请用户补充。

## 第一篇的独立官方资料

- https://docs.comfy.org/tutorials/flux/flux-2-klein
- https://huggingface.co/black-forest-labs/FLUX.2-klein-4B
- 本地官方模板：`.venv/Lib/site-packages/comfyui_workflow_templates_json/templates/image_flux2_klein_image_edit_4b_distilled.json`。
- 下载固定版本、字节数和 SHA-256 写入 `trials/2026-10-20-flux2-klein/download-manifest.json`，完成后每个文件另有校验收据。
- 与此前用户叫停的 FLUX.3 标准版不是同一模型；本轮按新请求测试第一篇所指定的 FLUX.2 Klein 4B 蒸馏版。该流程所需的 Flux2 VAE 会重新下载，之前删除的其他权重不恢复。

## 本机进展

- 三个权重均已通过字节数和 SHA-256 校验。
- 512² 文生图成功两次：CPU 文本编码基线 434.24 秒，GPU 文本编码（启用 FP8 参数）210.85 秒。两张均清楚生成橘猫、雨夜咖啡馆和 HELLO；含加载/初始化，不能作为严格编码速度倍率。
- 1024² 在第 3/4 步附近底层 Aborted，无输出。失败栈落在 `cast_to_device`，完整日志已保留。
- 随后候选恢复配置（关闭动态 VRAM、预留 2GB、FP8 文本编码）在 ComfyUI 启动阶段 `torch.cuda.mem_get_info` 中止；该配置的编辑能力尚未得到验证。
- 独立新 Python 进程也在显存查询阶段异常退出，没有执行到 16×16 小矩阵运算。不能仅凭 `cuda.is_available() == True` 认为 GPU 已恢复。
- 七项编辑案例已准备但尚未提交，列入 `trials/2026-10-20-flux2-klein/blocked.json`。需用户恢复 GPU 运行时后继续，先做 GPU 健康检查，再跑单图改色等任务。
- 当前已同步三项真实执行记录至旧功能报告（两项成功、一项失败），报告核验结果：27 个结果案例，PNG 绑定/元数据错误 0、缺失图片 0。
- GPU 阻塞证据：`trials/2026-10-20-flux2-klein/gpu-runtime-block.json`。

## 用户提供的离线正文（新增证据）

先前的浏览器访问受阻记录仍然成立；以下来自用户明确提供的本地离线副本。没有重新请求微信原文。

- Z-Image 老少皆宜新知识，AIO模型和工作流！；托尼不是塔克；2025-12-11T23:59:00+08:00。模型：Z-Image-Turbo-AIO FP8。正文路径：`[private-article-snapshot]`。原始 HTML SHA-256：`9946edf0d6aab4455debea11a3a38245a3b6084968527b7e4d4d57d5c5318179`。
- Z-Image很稳，低显存GGUF模型和工作流！；托尼不是塔克；2025-12-01T23:58:00+08:00。模型：jayn7/Z-Image-Turbo-GGUF Q4_K_M + unsloth/Qwen3-4B-GGUF Q4_K_M。正文路径：`[private-article-snapshot]`。原始 HTML SHA-256：`f496872caa051f7afdc9f41772a38f1f436a66eecb3a928221143b6d3c91a403`。

AIO 文中提到 NSFW，但重新打包或单文件布局本身不能证明经过特殊训练或能力增强；须独立核对模型卡，不能把所有社区模型都视为同一版本。10–40 秒、8GB、4步等均先记录为文章宣称。

## Z-Image 下载与未执行状态

四项权重共 18,159,309,094 bytes，均通过完整文件 SHA-256 校验。已准备 AIO 6 案例、双 GGUF 4 案例；两者均未提交推理，新增输出为零。

本轮新 GPU 探针仍在 `torch.cuda.mem_get_info` 原生中止，16×16 matmul 未到达；最新探针路径记录于 `trials/2026-10-20-zimage/preparation-status.json`。运行器验证会在不健康探针处拒绝提交。没有自动重启或重置驱动。

AIO 保留历史工作流 res_multistep/simple/shift3/CFG1，比较9/8/4步；GGUF保持公开示例Euler/simple/shift3/CFG1/9步。第一轮均降至512²，不能当1024²能力验证。GGUF编码器选择Q4_K_M，与文章截图Q4_K_S不同，已明确记录；没有取得作者私盘JSON。
