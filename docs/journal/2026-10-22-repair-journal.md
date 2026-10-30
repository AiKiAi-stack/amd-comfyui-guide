# 出图问题解决过程 · 2026-10-22

代码仓库：barely-comfy，分支 `fix/gguf-repeat-stability`。本记录接续提交 `96d6f12`，每项保留失败，不用后来成功覆盖原图。

本轮结果：Kroma 多图融合和 Turbo 遮罩变狐达到各自原案例目标；Qwen 精确人物身份仍部分达到。新增条件复用、参考VAE隔离与数值核对工具，原生卸载崩溃根因仍未修复。下面保留实际尝试顺序与失败。

## 验收与记录方式

运行成功、视觉目标通过、底层崩溃根因修复分别记录。每次记录输入、完整工作流、实际分阶段 API、输出、history 绑定、文件哈希、资源保护停止和目视判断。大模型顺序运行，测试进程退出后再启动下一项。

## E01 · 量化参数卸载探针

原始证据：Qwen 采样 OOM 清理和 Kroma attention OOM 清理都曾在 `unpatch_model → model.to → GGMLTensor.to` 出现 Windows access violation；另一条 INT8 文本卸载栈位于 `QuantizedTensor._handle_to`。这些栈不能直接证明是同一根因。

先构造 [最小探针](../../scripts/probe_quantized_offload.py)，调用已安装的真实 GGUFModelPatcher/ModelPatcher 和 Tensor.to，而非替身实现。GGUF 从原权重文件选取一块不超过16MiB的真实量化张量；INT8 使用8MiB的真实 TensorWiseINT8Layout 参数。各循环200次，交替普通卸载与可控 Python 异常后的卸载，每次校验原始量化数据 SHA。

首次运行：GGUF 200/200、INT8 200/200，数据一致，没有 native access violation。但两个进程在 Python 解释器退出时出现 ModelPatcher 析构 `CallbacksMP` 已为 None 的忽略异常，进程退出码仍为0。该异常与原 GPU 卸载访问冲突不同，原日志保留。探针随后在模块仍可用时显式 cleanup 并回收引用环，再独立复跑。

初步结论：小权重循环没有复现原故障，不能把探针通过称作完整模型或真实 OOM 恢复已修复；暂不对底层卸载路径实施猜测性补丁。

## E02 · Kroma 多参考融合：去除人工灰底

上一轮自然狐狸已出现、苔石和原猫重影消失，但灰色参考底板被迁入输出，视觉仍部分达到。

预测：移除人工灰底，恢复原场景参考并只裁取不含苔石的狐狸头/躯干，可消除灰板迁移；若重新出现猫形或融合缺陷，则参考内容干扰仍未解决。

本轮工作流：[自然裁切参考](../../trials/2026-10-21-repairs/workflows/kroma-multiref-natural-crop.api.json)。输出仍512²、4步、原seed，参考VAE按原比例使用384或256×384；保留最终局部合成及输入/遮罩附件。提示词同步改为替换原猫，避免继续要求填入已不存在的空白区域。该组合实验不能单独归因于裁切或文字，若有效再做消融。

状态：准备执行，实际结果后续追加。

## E03 · Turbo 猫形残留：清理采样初始 latent

检查原 API：TextEncodeQwenImage21 的图像1已抹去原猫，但采样初始 `VAEEncode` 仍使用原猫整图。遮罩只控制加噪与合成范围，不保证模型忘记原形。

预测：保持提示词、参考图、seed、8步sigmas和遮罩，仅将初始 VAE 输入改成同一抹猫图，若猫形减弱，则初始 latent 是一个可操作的影响因素；若仍像猫，不能认定该修改解决了物种替换。

本轮工作流：[清理初始潜空间](../../trials/2026-10-21-repairs/workflows/turbo-fox-clean-latent.api.json)。先尝试隔离 GPU 文本编码以缩短此前约14分钟的CPU编码；编码设备变化也会记录，不将设备变化掩盖成完全同条件。

状态：准备执行，实际结果后续追加。

## 后续记录

每次执行结束追加实际阶段、是否保护停止、图像目视结论和下一步；尚未执行的部分不计为通过。精确人物身份迁移仍在待办中，本轮不以发色相似代替身份验收。

E01 复跑结果：显式 cleanup 后两路仍各200/200，退出码均0，原始量化数据 SHA 不变，且解释器退出阶段的忽略异常消失。GGUF 的只读 NumPy mmap 警告与现有 loader 使用同一读取方式；探针没有写入映射。结构化结果见 [四次探针记录](../../trials/2026-10-22-unload/bounded-probes.json)。

## E04 · Qwen 仅换脸：真实 CFG 对照

上一轮保住黑发和侧转，但五官与雀斑身份不足。本轮只把 KSampler CFG 从1改为3，文本、参考、seed、15步、遮罩和原始条件完全保持。复用经图签名、输入时间与归档SHA检查的旧编码，不重新编造条件。预测：如果文字条件约束不足是主要因素，CFG3应提高目标面部特征遵循；如果仍只是泛化脸或出现过度引导，则继续登记部分达到。

[完整候选工作流](../../trials/2026-10-21-repairs/workflows/qwen-face-only-cfg3.api.json)。阶段内部沿用原案例名以验证编码复用，最终PNG使用新独立前缀。状态：准备执行。

E02 首次结果：完整编码/4步/解码通过，灰板、苔石与原猫重影消失，狐狸明确；但最终遮罩截止在y500，白尾尖被合成边界截断，仍部分达到。新的 E02b 仅扩大最终合成遮罩至图像底边并取消底边羽化，复用完全相同的编码/采样归档，检查尾部能否恢复；不重新采样，不将合成保护归因于模型。

E03 GPU 编码尝试：在 QwenImage21TEModel_ 加载阶段触发1024MiB commit保护，进程被主动停止；日志没有 native exception/OOM 标记，没有条件或PNG输出。原 summary/log 哈希将进入尝试索引，不把保护停止当作自然崩溃。

为避免重复约869秒的 CPU 文本编码，新增显式 --reuse-text-from：仅在正/负条件完整依赖图及输出槽位完全一致、源服务已退出、history成功、归档SHA匹配、旧输入时间早于编码时，复用旧条件；新初始latent仍由原VAE重算。改变提示词、参考图、CLIP依赖或输出槽位都拒绝复用，旧的全条件复用规则保持。图回归新增2项（含多个拒绝分支），共8项通过。

实际 CPU 条件刷新耗时4.48秒，仅加载VAE而没有重新加载文本模型；完整采样/解码与目视结果仍需另行核对。该数字仅是提交至history的刷新阶段，排除服务冷启动，不是整个端到端耗时。

E03 完整结果：8步采样与解码完成。旧/新归档逐张量核对，正负条件完全一致、noise_mask一致、新初始samples确实改变（7个张量、6个基础值通过精确检查）；仍主要为圆头猫形背影，并有灰色边框迁移。仅清理初始latent并未解决物种替换，原假设不足。

E04 首次 CFG3 运行：首步前触发 commit 保护，manual cast日志为F32，没有PNG，没有native/OOM标记。后续将显式 FP16 UNet 加 attention升精度，且补做相同FP16的CFG1控制，避免把精度变化错误归因于CFG。

## E05 · Turbo 明确侧转长吻与自然参考

追加组合实验：保持背向身体，但明确要求右转侧脸、可见长吻；图像参考恢复原场景与自然裁切狐狸，初始latent仍抹去旧猫，消除人工灰板线索。编码阶段只额外尝试CPU VAE半精度以减少此前1.29GB VAE权重占用，再尝试独立GPU文本编码。此为组合配方探索，不把成功归因于某个单因素；半精度参考也不是旧参考的数值等价替代。若再次保护停止，保留失败而不放宽保护阈值。

E02b 结果：沿用相同采样SHA，仅重新CPU解码与扩大合成范围，9.078秒提交至history，完整白尾尖恢复；灰板、苔石和原猫重影均消失。[结果](../../trials/2026-10-21-repairs/cases/kroma-multiref-full-tail/result.json)。原案例雨街+狐狸主体目标通过；精确动物身份与两参考的因果消融仍未验收。遮罩外保留由最终合成提供。

E03 条件数值核对：[精确比较结果](../../trials/2026-10-21-repairs/cases/turbo-fox-clean-latent/exact-conditions.json)，可用 scripts/verify_reused_conditions.py 读取phase-link重新执行。仅清理初始latent没有解决物种替换，这条失败判断保留。

## 重跑条件复用的方法

在安装了 psutil、Torch 和 safetensors 的已有运行环境中执行，输出目录必须是新的。完整原工作流保留文本编码路径，实际编码API明确记录LoadRepairConditioning，phase-link保留来源API/history/SHA与输入核对。若文本条件改变，重新编码而不放宽验证。

```powershell
python scripts/run_conditioned_repair.py --runtime D:\MyProject\amd_comfy `
  --workflow trials/2026-10-21-repairs/workflows/turbo-fox-clean-latent.api.json `
  --reuse-text-from runs/turbo-fox-v1/encoding/cases/turbo-mask-fox-reference `
  --encoding-profile cpu-text --sampling-profile gpu-text `
  --sample-extra-arg=--fp16-unet --sample-extra-arg=--force-upcast-attention `
  --isolate-sampling --isolate-decode --out runs/turbo-clean-latent-new
```

本机已有G盘解释器和模型缓存还可分别通过 --python-executable、--model-paths 指定。默认commit保护阈值保持1024MiB，本轮没有更改系统pagefile、驱动或模型权重。

E04 相同FP16对照结果：CFG1和CFG3均完成15步与独立解码，采样日志分别58.80秒和112.60秒。实际采样图逐字段比较，除归档provenance摘要外，仅case03_5.inputs.cfg不同；编码归档SHA相同。[控制变量核对](../../trials/2026-10-22-unload/cfg-control.json)。两张均保住黑发、侧转和服装；CFG3有较清楚的雀斑与绿眼，但鼻/眼/脸部比例仍未证明与A一致，身份仍部分达到，不能认定提高CFG已修复身份。

E05 半精度CPU VAE的权重日志为644.19MB（原1288.38MB），但在进入文本编码前持续数分钟，CPU计算变慢；停止这一变体，并另存operator-stop.json。controller记录的服务退出由本次主动停止引起，不是native crash。内存较少不等于可用配方，阈值未放宽。

## E06 · 独立预计算参考 VAE，再加载GPU文本模型

新的四阶段运行器先在CPU进程用F32 VAE计算参考latent和初始latent，保存带SHA的归档并退出，再在不加载VAE的GPU文本进程中调用原TextEncodeQwenImage21。它保留原节点的实际尺寸处理、alpha合成、keep_vision=False与参考latent插入，避免用删除VAE或删除参考图冒充等价降内存。

差分测试直接与已安装的原节点比较：非方形RGBA、多参考、独立初始latent/遮罩，以及无效归档拒绝，共3项通过。图裁剪检查证明参考阶段不加载文本/扩散模型、文本阶段不加载VAE；图回归共10项通过，原归档6项仍通过。

[四阶段运行器](../../scripts/run_qwen_reference_repair.py)与[参考等价性测试](../../scripts/test_qwen_reference_phases.py)纳入仓库。接下来实际重跑E05的自然参考/侧转长吻配方；这仍是内存隔离规避，不声明修复HIP原生卸载。

E06 实图：完整8步及解码完成，右侧转长吻已是明确狐狸，背向身体保留；但右侧仍有旧主体/合成边界残影，尾部也靠近旧遮罩边缘，整图仍部分达到。新四阶段方案没有更换原权重，也没有把reference latent删除。

E06b 追加：沿用E06相同正负条件及初始samples，只把采样noise_mask与最终合成mask扩大到图像右/下边界，去掉右/下羽化，消除旧遮罩外的猫体残留。抹猫VAE输入仍保留原窄遮罩，与E06的初始samples一致；仅改变可编辑范围。发布完整可重算源图与实际缓存执行图，避免把不同图的摘要混为同一个。

E06 实际资源与计时：[阶段资源记录](../../trials/2026-10-22-unload/memory-comparison.json)。日志计算时间为参考VAE10.56秒、GPU文本35.89秒；四阶段提交至history耗时相加约142.47秒，排除冷启动。GPU文本进程峰值RSS观测约11.74GB，可用物理内存最低约94MB、commit余量最低约2.20GB；不是低RAM或长期稳定通过，2秒采样也不是精确硬件峰值。失败尝试被更早停止，不能用两次RSS直接比较内存需求。

E06 真实归档核对：两路参考在正/负条件中共4份tensor逐值、逐dtype相等，初始samples和noise_mask也完全一致，见 [实际参考比较](../../trials/2026-10-21-repairs/cases/turbo-fox-profile-precomputed/exact-reference-latents.json)。预处理的3个差分测试使用观察用CLIP/VAE检查原节点接口；本次真实VAE、真实GPU文本编码与实图是另一个验收层次。

E06b 结果：[扩大采样/合成遮罩的狐狸](../../trials/2026-10-21-repairs/cases/turbo-fox-profile-wide-mask/result.json)。完整8步、CPU解码并目视通过原案例的猫变狐目标；狐狸保持背向身体、侧转长吻和白尾尖，旧猫边缘残影消失。尾部接近右下画幅，未验证精确动物身份。遮罩外181024像素无变化，按实际float mask支持和8bit附件核对一致。

[控制变量核对](../../trials/2026-10-21-repairs/cases/turbo-fox-profile-wide-mask/exact-mask-change.json)：正负条件和初始samples完全相同，只改变noise_mask；刷新归档约3.03秒，不重新加载文本或VAE模型。完整源工作流可用四阶段运行器重新计算，实际缓存执行图另存，摘要和上游引用分别记录。

## 本轮验证与保留失败

[29项回归及1个预期失败对照](../../trials/2026-10-22-unload/verification.json)全部符合预期。标准尝试索引共88条已结束的阶段记录，不代表88项功能通过。[GPU文本加载保护停止](../../trials/2026-10-22-unload/attempts/turbo-gpu-text-guard/result.json)、[默认F32 CFG3保护停止](../../trials/2026-10-22-unload/attempts/qwen-cfg3-f32-guard/result.json)、[CPU半精度VAE过慢后主动停止](../../trials/2026-10-22-unload/attempts/turbo-cpu-fp16-vae-slow/result.json)分别保留执行图与日志SHA；后者观测窗口约423.9秒，未当成自然崩溃。

精确人物身份、参考消融、原CPU完整自动反推以及量化卸载native根因仍未结案。四阶段成功是实际配方规避，不能回填为历史崩溃已修复。

最终总报告核对82条结果记录：图片绑定/元数据错误0、报告缺图0。这个数字包括历史失败、素材、诊断和独立重试，不代表82项功能全部通过。代码和运行时辅助节点文件SHA一致；系统pagefile、驱动与原权重未更改。

## E07 · 用户要求扩大排查覆盖面

重新把原19条欠项逐条映射到独立重试，额外补入Turbo角色、姿态、多参考和对照。可机读清单见[覆盖记录](../../trials/2026-10-22-coverage/coverage.json)。queued表示仅准备，不能算已执行。当前完整修复目标仍未全部达到。

修改参考隔离运行器支持多个独立workflow：先在一个CPU服务顺序预计算参考，再在一个服务顺序编码，随后每个案例独立采样和解码。运行前校验所有图和唯一标签；每个案例独立保留原图SHA、缓存图SHA、参考archive SHA和phase-link，不将多项证据混为一次。11项图测试通过，包含真实姿态/融合图的参考独立性和重复标签拒绝。

首次实际批次的5个参考预处理与5个编码均成功：UN姿态、UN融合、有/无狐狸参考，以及相同扩散权重/seed/提示下普通编码器角色与姿态。UN到普通INT8编码器的正常切换没有复现旧native退出；此结果不覆盖OOM清理。采样/解码及目视结论另记。

E07a角色图完整输出：宇航服去除、红卷发女性户外服、丛林与主要构图保留；精确身份和细节不充分，部分达到。

再次核对BFS作者[Qwen指南](https://huggingface.co/Alissonerdx/BFS-Best-Face-Swap/blob/main/docs/qwen-image-2.1.md)：Pruna可禁用，属于可选加速器。缺少它不是继续BFS测试的阻塞。15步GGUF实验仍不是作者列出的int8整包与8步参数复现；本轮补前缀/LoRA消融。

E07b 实际参考消融：UN融合保留同一prompt、seed和扩散权重，去掉第二张狐狸参考后仍生成清晰狐狸。两图结果并不能证明精确参考身份，提示文本本身足以给出狐狸语义。带参考图的尾部仍出框，继续记部分达到。配对结果见[two-ref](../../trials/2026-10-21-repairs/cases/turbo-un-multiref-natural/result.json)与[no-fox](../../trials/2026-10-21-repairs/cases/turbo-un-multiref-no-fox/result.json)。

E07c 同条件普通编码器对照：角色和姿态都可完成主要语义，单个配对看不出足以验收的UN优势；两者精确人物身份都未通过。没有将两组看起来相似改写为编码条件数值等价，也没有从单例外推所有人物。

E07d 所有6个四阶段新案例（独立角色+5项批处理）的真实archive已核对：预计算参考latent在正/负条件内逐dtype、逐值相等，初始latent保持。每项公开目录有exact-reference-latents.json、reference-link.json、原始完整工作流、实际cached-execution-workflow与四阶段耗时。计时不含冷启动。

## E08 · CPU反推重试与Kroma参考路径核查

同一8B W4A8权重改为CPU FP32，并设置6个计算线程、保留分块词表投影。日志确认实际dtype=float32；首token372.31秒，第二个约582秒。约664秒观察仍只有2/40，实际发出停止前继续保留日志，没有完整描述或新图。FP32没有实质解决自回归延迟；操作员停止原因独立保存在raw run，不能称native崩溃或CPU任务通过。排入已有4B FP8模型的CPU描述替代路径，模型变化单独标记。

Kroma裁切头部重试仍残留黑发和黄色领口。继续尝试：只清除扩散参考latent中的旧头部，保留原视觉姿态参考。另检查当前核心Krea2：已经实现ref_latents，因此没有按插件README的旧描述误判“核心完全不支持参考”，没有安装该插件；只在D盘vendor目录克隆源码审阅，版本13ef60f。

发现本机index_timestep_zero会给参考token独立t0，而Krea编辑源码对参考/目标共享时间条件。准备index的8步对照，以及相同条件加Krea BFS LoRA的兼容性实验。不能先认定这是Kroma错误配方的根因。新增LoRA存G盘，914159816字节、SHA256 abc6c468c578b36e6bd960106ad5886afd3f5321e4fe2de26c05bb5c6585b836完全匹配作者LFS指针；来源与兼容性限定见[审计记录](../reference/research/kroma-bfs-compatibility-2026-10-22.json)。这是Krea权重在Kroma OPD Q2_K上的实验，不是官方Kroma BFS支持声明。

## E09 · 首次真实正常卸载复现

新增运行器--unload-between：每次成功采样后调用真实/free，等待进程内GPU allocator保留内存低于256MiB再提交下一次。三次Qwen完整模型循环通过：第一次卸载前4435476480字节，后67108864；其后两次前4276092928、后67108864。不是仅杀进程或小张量探针。

Kroma在第一张4步采样/有限latent保存成功后，正常/free即0xC0000005退出，栈GGMLTensor.to→Module._apply→GGUFModelPatcher.unpatch_model。无OOM标记。完全相同工作流加--disable-pinned-memory仍复现，因此拒绝“关闭锁页即可修复”假设。原始两次日志、实际工作流和退出码保留。新增显式诊断节点TraceRepairGgufUnloads，只在显式接入时记录unpatch时每个参数to前后；不修改Torch/GGUF原代码，不把诊断当修复。下一步定位最后一个参数设备和搬运方式。
