# 新模型待测清单

1. [用户新增的微信文章](https://mp.weixin.qq.com/s/-_od9lqhL1jMXxvzNdzAVQ)（2026-10-19 登记）
   - 模型：**Flux.3-5.6B-UN**（用户在原会话后续消息补充，2026-10-20 恢复）。微信正文仍未读取。
   - 用户称今天发布，原始发布日期尚未核实。
   - 来源：[夸克整合包](https://example.invalid/private-share-removed)；[作者云镜像](https://www.compshare.cn/images/uc0UnUzrIbtD)。镜像页标示 v1.0、2026-10-18 更新，声明 4 步、8GB、文生图、图像编辑、图生图、自动提示词、批量任务；不是已核实的微信发布日期。
   - 本轮浏览器复核：4 个分卷 `Flux.3-Image-5.6B-UN.part{1,2,3,4}.rar`，页面合计 36.2G，前三个各 9.8G、第四个 6.9G。当前页面要求扫码或手机号登录；未下载、未解包、未核验内部权重。
   - 排期：接在当前五组模型的功能测试之后。公开 FLUX 3 Klein 和 Sakura UN 编码器仅是候选，不能据此称复现作者 4 步整合包。
   - 结果：尚无本机输出，不计入已测试成功项目。
   - [详细来源与本机候选审计](flux3-un-source-audit-2026-10-20.md)。当前阻塞是取得整合包内的精确权重和工作流；不能以标准Klein候选冒充UN。
   - 2026-10-20 最新指示：停止标准版替代下载／测试，改查 Hugging Face 同名版本。标准 ModelScope 三个组件已在指示到达前下载校验完毕，但未提交推理；服务器已停止，文件保留。HF 候选仅读取模型卡和元数据，未下载权重。
   - [HF 同版检索](flux3-hf-exact-version-search-2026-10-20.md)：两个精确名称无命中；Sakura UN 编码器和独立四步 LoRA 均未能与作者整合包建立同版映射，继续 pending。
   - [作者镜像工作流检查](flux3-author-workflow-access-2026-10-20.md)：公开页无下载入口，三个 PNG 无 ComfyUI 工作流元数据；实例内部未知。

机器可读状态见 [pending-models.json](./pending-models.json)。

2026-10-20：按用户要求，已删除此前 ModelScope 下载的三个标准版权重，共 11,022,645,311 字节（10.27 GiB）。仅保留小工作流和历史校验记录；详见 	rials/2026-10-20-flux3/modelscope-weights-deleted.json。
