# 来源与本机部署

用户提供的标题对应[刘悦的技术博客在优云智算发布的镜像说明](https://www.compshare.cn/images/rGwg8DDReAEc)，更新于2026年10月25日。页面描述包含1G显存、长文本、声音克隆、文本指令和音色设计，并给出GET API示例。它是云镜像介绍，没有公开完整的低显存实现和可核对的显存测试条件。

本应用使用[官方Ming-3.0-tts代码](https://github.com/inclusionAI/Ming-3.0-tts)，固定到`028c1eace193e7acdb256453da89b6e9207e052b`；使用[官方0.5B权重](https://huggingface.co/inclusionAI/Ming-3.0-tts-0.5B)，固定到`8d66b70a00f05ad183fa8a863b4ce609fc83cbc0`。没有使用云镜像，也没有接入ComfyUI。

官方环境主要面向NVIDIA。这里使用AMD为gfx1032提供的PyTorch 2.12 / ROCm 7.14包。显存与速度须由本机实际生成音频后记录，不能直接沿用镜像标题的1G说法。

已确认的音频依赖问题：AMD提供的torchaudio 2.11.0.2原生扩展导入时报`undefined symbol: torch_exception_get_what_without_backtrace`。Ming需要的SoundFile读写、Resample与Kaldi fbank均由torchaudio 2.6的Python/Torch代码实现。本应用从PyTorch官方`v2.6.0`源码构建`2.6.0+pythononly`，仅在构建脚本中关闭原生扩展；没有改写这些音频算法。音频读写、重采样及80维说话人特征检查位于`test_audio_runtime.py`。

`patches/ming-progress.patch`仅向官方分段循环添加可选进度回调，让页面显示正在生成第几段；不改变提示词、分段或采样算法。

存储：KEKE最初以只读挂载，已在无force选项下成功重新挂为可写。约3GB权重已移到KEKE，逐文件SHA256验证通过。Docker和containerd分别使用KEKE上独立ext4存储区的子目录。这个存储区是NTFS盘内一个48GiB文件，不是新分区；服务依赖挂载成功才启动，避免盘未挂载时写入根分区。

参考：[Docker存储驱动支持的文件系统](https://docs.docker.com/engine/storage/drivers/select-storage-driver/)、[Docker官方Ubuntu安装方法](https://docs.docker.com/engine/install/ubuntu/)、[AMD容器GPU设备说明](https://rocm.docs.amd.com/en/develop/install/docker-containers.html)。
