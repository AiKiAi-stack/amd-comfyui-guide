# Ming 本地语音工作台

使用 Ming-3.0-TTS-0.5B 的独立 Gradio 页面，不依赖 ComfyUI。支持内置音色、参考音频声音克隆、文字描述音色、表演指令和本机 API。

来源是[刘悦的镜像说明](https://www.compshare.cn/images/rGwg8DDReAEc)，实现使用[官方推理代码](https://github.com/inclusionAI/Ming-3.0-tts)及[官方权重](https://huggingface.co/inclusionAI/Ming-3.0-tts-0.5B)。镜像页面的“1G显存可用”没有公布测试条件，本项目以实际运行数据为准。[来源及兼容处理](research/sources.md)。

[查看本机实测与音频样例](research/test-results.md)。

## 在本机启动

已构建镜像后：

```bash
bash start.sh
```

打开 <http://127.0.0.1:7861>。关闭：`sudo docker compose down`。查看日志：`sudo docker compose logs --tail 100 -f`。停止或重建容器会保留模型和已生成音频。

页面先填写朗读文字，然后选择生成方式：

- **内置音色**：选择音色后生成。
- **声音克隆**：上传参考音频，填写音频中实际说出的文字。建议使用3到15秒清晰单人讲话；当前接受1到30秒。
- **音色设计**：填写声音特征，如“温暖、沉稳的青年男声”。
- **表演指令**：填写朗读要求，如“先轻声安慰，最后一句语气坚定”。这与克隆音色是分开的任务模式。

长文可以直接粘贴或上传txt。应用调用官方按句分段流程，逐段合成后拼接；一次最多五万字，超过时提示拆分，不会静默截断。这里的“五万字”是输入上限，不表示已完成五万字连续合成测试。页面显示音频长度、生成耗时、显存峰值、分段数和随机种子。首次模型加载时间另计。暂时不用时可点击“释放模型占用的显存”，给其他GPU应用腾出空间。

## 存储

本机配置在`.env`，示例见`.env.example`：

| 内容 | 本机位置 |
| --- | --- |
| 模型权重，只读挂入容器 | `/media/wbb/KEKE/AIModels/Ming-3.0-tts-0.5B` |
| 输出WAV及每次请求的数据 | `/media/wbb/KEKE/Apps/ming-tts/data/outputs` |
| 上传临时文件、缓存 | `/media/wbb/KEKE/Apps/ming-tts/data` |
| Docker镜像和构建缓存 | `/media/wbb/KEKE/LinuxContainers/docker` |
| containerd数据 | `/media/wbb/KEKE/LinuxContainers/containerd` |

KEKE是NTFS。容器存储使用盘内48GiB的ext4文件，挂载到`LinuxContainers`；没有修改分区。宿主机Docker和containerd服务要求该目录已挂载，防止盘未就绪时写进根分区。系统配置备份放在`LinuxContainers/backups`。`ops/`是这台机器的一次性安装记录，其他机器需按实际磁盘调整，不能照搬格式化路径。

## API

简单GET调用，返回WAV：

```bash
curl --get http://127.0.0.1:7861/api \
  --data-urlencode 'text=你好，欢迎使用本地语音工作台。' \
  --data-urlencode 'speaker=灵小柔' \
  --data-urlencode 'seed=1895' -o speech.wav
```

POST JSON，支持内置音色、音色设计和表演指令：

```bash
curl http://127.0.0.1:7861/api/tts -H 'Content-Type: application/json' \
  -d '{"text":"傍晚的风从山口吹过来。","mode":"音色设计","instruction":"温暖、沉稳的青年男声"}' \
  -o speech.wav
```

声音克隆使用Gradio客户端上传文件，不接受任意服务器文件路径。完整参数以页面下方“通过API使用”为准：

```python
from gradio_client import Client, handle_file

result = Client("http://127.0.0.1:7861").predict(
    text="这是需要用参考音色朗读的新文字。",
    mode="声音克隆", speaker="灵小柔",
    reference_audio=handle_file("reference.wav"),
    reference_text="参考音频里实际说出的逐字文字。",
    instruction="", language="中文", seed=1895, segment_length=24,
    api_name="/synthesize",
)
print(result)
```

HTTP接口说明在 <http://127.0.0.1:7861/docs>。请求由同一把模型锁串行执行，避免不同请求修改种子或同时推理。

## 重建与检查

从仓库新下载本应用时，先安装兼容的Docker和AMD驱动，复制`.env.example`为`.env`并按实际路径修改。创建目录并构建镜像，然后用一次性容器下载固定版本的官方权重。下面是当前这台机器的路径；代理不需要时删除对应`-e HTTPS_PROXY`参数。

```bash
cp .env.example .env
mkdir -p /media/wbb/KEKE/AIModels/Ming-3.0-tts-0.5B
mkdir -p /media/wbb/KEKE/Apps/ming-tts/data/{outputs,tmp,cache}
bash build.sh
sudo docker run --rm --network host -u "$(id -u):$(id -g)" \
  -e HF_HUB_OFFLINE=0 -e HF_HUB_DISABLE_XET=1 \
  -e HTTPS_PROXY=http://127.0.0.1:7897 \
  -v /media/wbb/KEKE/AIModels/Ming-3.0-tts-0.5B:/models \
  -v /media/wbb/KEKE/Apps/ming-tts/data:/data \
  ming-tts-webui:local python -c "from huggingface_hub import snapshot_download; snapshot_download('inclusionAI/Ming-3.0-tts-0.5B', revision='8d66b70a00f05ad183fa8a863b4ce609fc83cbc0', local_dir='/models', allow_patterns=['*.json','*.txt','*.safetensors','*.onnx'])"
bash start.sh
```

日常重建与检查：

```bash
bash build.sh
sudo docker compose run --rm --no-deps webui python -m unittest -v test_requests.py test_audio_runtime.py test_api.py
bash start.sh
```

`build.sh`从Compose配置生成构建参数。构建阶段访问宿主机网络以使用本机下载代理；运行时使用Docker默认隔离网络，只将7861端口绑定到本机。容器以UID 1000运行，仅提供KFD和对应GPU设备，无特权模式。不同机器需修改设备所属组、模型目录和数据目录。

需要复测某一项时，可以在服务启动后运行下列命令。将`preset`替换为`clone`、`long`、`design`或`freeform`可选择其他测试；每次会实际生成音频并保存记录，长文会花数分钟。

```bash
sudo docker compose exec -T webui python tools/smoke_api.py preset --output /data/verification
```

本机为RX 6650 XT，镜像固定使用`torch[device-gfx1032]==2.12.0+rocm7.14.0`；它不是通用NVIDIA镜像。容器隔离软件依赖，仍与其他应用共享显卡和显存。不要同时启动多个合成服务。
