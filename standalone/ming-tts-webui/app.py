"""Run with .venv/bin/python app.py; binds only to localhost."""
import logging
import os
from pathlib import Path

os.environ.setdefault("GRADIO_ANALYTICS_ENABLED", "False")
os.environ.setdefault("GRADIO_TEMP_DIR", str(Path(__file__).resolve().parent / ".gradio-tmp"))

import gradio as gr
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from engine import MODES, LANGUAGES, VOICES, OUTPUTS, Request, engine, read_text_file


def generate(text, mode, speaker, reference_audio, reference_text, instruction, language, seed,
             segment_length, progress=gr.Progress()):
    try:
        path, m = engine.synthesize(Request(text, mode, speaker, reference_audio, reference_text,
                                           instruction, language, int(seed), int(segment_length)), progress)
        summary = (f"已生成 {m['audio_seconds']:.1f} 秒音频 · 合成用时 {m['generation_seconds']:.1f} 秒 · "
                   f"峰值显存 {m['peak_allocated_mib']:.0f} MiB · 种子 {m['seed']}")
        return path, summary, path, m
    except Exception as exc:
        logging.exception("Speech generation failed")
        raise gr.Error(str(exc)) from exc


def load_text(path):
    try:
        return read_text_file(path) if path else gr.skip()
    except ValueError as exc:
        raise gr.Error(str(exc)) from exc


def mode_changed(mode):
    return (gr.update(visible=mode == "内置音色"),
            gr.update(visible=mode == "声音克隆"),
            gr.update(visible=mode in ("音色设计", "表演指令"),
                      label="音色描述" if mode == "音色设计" else "表演要求"))


CSS = """
.gradio-container {max-width:1120px!important; margin:auto;}
#intro {padding:12px 0 22px;}
#intro h1 {letter-spacing:-.03em; font-size:2rem;}
#result {background:var(--background-fill-secondary); border-radius:16px; padding:20px;}
button:focus-visible, a:focus-visible {outline:3px solid #367862!important;outline-offset:3px;}
@media(prefers-reduced-motion:reduce){*{scroll-behavior:auto!important;}}
"""

with gr.Blocks(title="Ming · 本地语音工作台", theme=gr.themes.Soft(primary_hue="emerald"), css=CSS) as demo:
    gr.Markdown("# Ming · 本地语音工作台\n输入文字，选择音色，生成可下载的语音。Ming-3.0-TTS-0.5B · 本机运行", elem_id="intro")
    with gr.Row():
        with gr.Column(scale=3):
            text = gr.Textbox(label="要朗读的文字", lines=10, max_lines=24,
                              value="傍晚的风从山口吹过来，远处的云慢慢染成了金色。",
                              placeholder="粘贴文章，或上传txt文件。长文自动按句分段，最多五万字。")
            text_file = gr.File(label="也可上传txt文件（UTF-8或GB18030，最多1 MB）", file_types=[".txt"], type="filepath")
            mode = gr.Radio(MODES, value="内置音色", label="生成方式")
            speaker = gr.Dropdown(VOICES, value="灵小柔", label="内置音色", filterable=True)
            with gr.Group(visible=False) as reference_group:
                gr.Markdown("上传一段3到15秒的清晰单人讲话，再填入这段音频的逐字文字。")
                reference = gr.Audio(label="参考音频", sources=["upload", "microphone"], type="filepath", format="wav")
                transcript = gr.Textbox(label="参考音频的准确文字", lines=2)
            instruction = gr.Textbox(label="音色描述", lines=3, visible=False,
                                     placeholder="例如：温暖、沉稳的青年男声，像在讲睡前故事。")
            with gr.Accordion("更多设置", open=False):
                language = gr.Dropdown(list(LANGUAGES), value="中文", label="朗读语言")
                seed = gr.Number(value=1895, minimum=-1, maximum=2147483647, precision=0,
                                 label="随机种子（-1为随机）")
                segment = gr.Slider(12, 96, value=24, step=1, label="每段目标长度",
                                    info="默认24。按标点分段，长文会逐段生成后拼接；没有标点的长句可能超过目标长度。")
            submit = gr.Button("生成语音", variant="primary", size="lg")
        with gr.Column(scale=2, elem_id="result"):
            audio = gr.Audio(label="生成结果", type="filepath", interactive=False)
            status = gr.Textbox(label="生成状态", value="等待生成。首次使用需要加载模型。", interactive=False, lines=3)
            download = gr.File(label="下载WAV音频", interactive=False)
            release = gr.Button("释放模型占用的显存", size="sm")
            with gr.Accordion("本次运行数据", open=False):
                metrics = gr.JSON(label="耗时、显存及种子")
            gr.Markdown("长文生成可能需要数分钟。页面显示实际合成用时；首次加载模型的时间单独记录。")
    with gr.Accordion("通过API调用", open=False):
        gr.Markdown('''简单调用，返回WAV音频：
```bash
curl --get http://127.0.0.1:7861/api --data-urlencode 'text=你好，欢迎使用本地语音工作台。' --data-urlencode 'speaker=灵小柔' -o speech.wav
```
声音克隆可用下方“通过API使用”中的 `/synthesize`，通过客户端上传参考音频，并提供准确转录。`/docs` 提供内置音色、音色设计和表演指令的JSON接口说明。''')
    text_file.change(load_text, text_file, text, api_name=False)
    mode.change(mode_changed, mode, [speaker, reference_group, instruction], api_name=False)
    release.click(engine.unload, outputs=status, api_name=False)
    submit.click(generate, [text, mode, speaker, reference, transcript, instruction, language, seed, segment],
                 [audio, status, download, metrics], api_name="synthesize", concurrency_limit=1)


class TTSBody(BaseModel):
    text: str = Field(min_length=1, max_length=50000)
    mode: str = "内置音色"
    speaker: str = "灵小柔"
    instruction: str = ""
    language: str = "中文"
    seed: int = Field(default=1895, ge=-1, le=2147483647)
    segment_length: int = Field(default=24, ge=12, le=96)


app = FastAPI(title="Ming 本地语音 API")


def api_response(request):
    try:
        if request.mode == "声音克隆":
            raise ValueError("声音克隆请使用Gradio客户端的/synthesize上传音频；不接受服务器文件路径。")
        path, m = engine.synthesize(request)
        return FileResponse(path, media_type="audio/wav", filename=Path(path).name,
                            headers={"X-Audio-Seconds": str(m["audio_seconds"]),
                                     "X-Generation-Seconds": str(m["generation_seconds"]), "X-Seed": str(m["seed"])})
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:
        logging.exception("API synthesis failed")
        raise HTTPException(500, str(exc)) from exc


@app.get("/api")
def simple_api(text: str, speaker: str = "灵小柔", seed: int = 1895, language: str = "中文"):
    return api_response(Request(text=text, speaker=speaker, seed=seed, language=language))


@app.post("/api/tts")
def json_api(body: TTSBody):
    return api_response(Request(**body.model_dump()))


@app.get("/health")
def health():
    return {"status": "ok", "model_loaded": engine.model is not None}


app = gr.mount_gradio_app(app, demo.queue(default_concurrency_limit=1, max_size=8), path="/",
                         allowed_paths=[str(OUTPUTS)], max_file_size="25mb")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=os.environ.get("MING_HOST", "127.0.0.1"), port=int(os.environ.get("MING_PORT", "7861")))
