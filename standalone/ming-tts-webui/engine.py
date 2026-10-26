"""Local Ming inference shared by Gradio and the HTTP API."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import os
import random
import sys
import threading
import time
import uuid

ROOT = Path(__file__).resolve().parent
UPSTREAM = ROOT / "upstream"
OUTPUTS = Path(os.environ.get("MING_OUTPUT_DIR", str(ROOT / "outputs")))
MODEL_PATH = Path(os.environ.get("MING_MODEL_PATH", "/models"))
MODES = ("内置音色", "声音克隆", "音色设计", "表演指令")
LANGUAGES = {"中文": "Chinese", "English": "English", "日本語": "Japanese",
             "한국어": "Korean", "Deutsch": "German", "Français": "French", "Español": "Spanish"}


VOICES = json.loads((ROOT / "voices.json").read_text())


@dataclass
class Request:
    text: str
    mode: str = "内置音色"
    speaker: str = "灵小柔"
    reference_audio: str | None = None
    reference_text: str = ""
    instruction: str = ""
    language: str = "中文"
    seed: int = 1895
    segment_length: int = 24

    def validate(self):
        self.text = self.text.strip()
        if not self.text:
            raise ValueError("请先输入要朗读的文字。")
        if len(self.text) > 50000:
            raise ValueError("一次最多提交五万字，请把更长的文章分批提交；文字不会被截断。")
        if self.mode not in MODES or self.language not in LANGUAGES:
            raise ValueError("请选择页面提供的生成方式和语言。")
        if self.mode == "内置音色" and self.speaker not in VOICES:
            raise ValueError("没有这个内置音色，请从音色列表中选择。")
        if self.mode == "声音克隆" and (not self.reference_audio or not self.reference_text.strip()):
            raise ValueError("声音克隆需要参考音频及其准确的逐字文字。")
        if self.mode in ("音色设计", "表演指令") and not self.instruction.strip():
            raise ValueError("请填写音色描述或表演要求。")
        if not 12 <= self.segment_length <= 96:
            raise ValueError("分段长度须在12到96之间。")
        if not -1 <= self.seed <= 2147483647:
            raise ValueError("种子须为-1或0到2147483647之间的整数。")


def read_text_file(path):
    data = Path(path).read_bytes()
    if len(data) > 1024 * 1024:
        raise ValueError("文本文件最多1 MB。")
    for encoding in ("utf-8-sig", "gb18030"):
        try:
            text = data.decode(encoding)
            if len(text) > 50000:
                raise ValueError("文本文件超过五万字，请拆分后上传。")
            return text
        except UnicodeDecodeError:
            pass
    raise ValueError("无法读取文字，请另存为UTF-8格式的txt文件。")


class Engine:
    def __init__(self):
        self.lock = threading.Lock()
        self.model = None

    def unload(self):
        with self.lock:
            if self.model is not None:
                import gc
                import torch
                self.model = None
                gc.collect()
                torch.cuda.empty_cache()
        return "模型已卸载，显存已释放。下次生成时会重新加载。"

    def synthesize(self, request: Request, progress=lambda *_args, **_kw: None):
        request.validate()
        with self.lock:
            import numpy as np
            import soundfile as sf
            import torch

            torch.set_num_threads(6)
            if not torch.cuda.is_available():
                raise RuntimeError("没有可用的AMD/NVIDIA GPU，请检查启动日志中的设备信息。")
            if request.mode == "声音克隆":
                info = sf.info(request.reference_audio)
                if not 1 <= info.duration <= 30:
                    raise ValueError("参考音频须为1到30秒，建议使用3到15秒的清晰单人讲话。")
            progress(0, desc="准备模型，首次生成需要加载权重…")
            load_start = time.perf_counter()
            if self.model is None:
                if not (MODEL_PATH / "model.safetensors").exists():
                    raise RuntimeError("找不到完整模型，请按使用说明下载权重，再检查模型目录。")
                sys.path.insert(0, str(UPSTREAM))
                from ming_tts import MingTTS
                self.model = MingTTS(str(MODEL_PATH), text_normalization=True)
            load_seconds = time.perf_counter() - load_start
            seed = request.seed if request.seed >= 0 else random.SystemRandom().randrange(2147483648)
            random.seed(seed)
            np.random.seed(seed)
            torch.manual_seed(seed)
            # Prompt encoding consumes RNG; clear between jobs so seed reuse is reproducible.
            self.model._prompt_cache.clear()
            kwargs = {"task": "IP", "controls": {"ip": request.speaker}}
            if request.mode == "声音克隆":
                kwargs = {"task": "TTS", "prompt_wav_path": request.reference_audio,
                          "prompt_text": request.reference_text.strip(), "use_spk_emb": True}
            elif request.mode == "音色设计":
                kwargs = {"task": "VOICE_DESIGN", "controls": {"style": request.instruction.strip()},
                          "use_zero_spk_emb": True}
            elif request.mode == "表演指令":
                kwargs = {"task": "FREEFORM", "instruction": request.instruction.strip(),
                          "use_zero_spk_emb": True}
            fragments = self.model.prepare_text(request.text, kwargs["task"],
                                                LANGUAGES[request.language], request.segment_length)
            torch.cuda.synchronize()
            torch.cuda.reset_peak_memory_stats()
            started = time.perf_counter()
            progress(0.1, desc=f"正在生成，共{len(fragments)}段，请稍候…")
            waveform = self.model.synthesize(text=request.text, language_id=LANGUAGES[request.language],
                                             max_length=request.segment_length,
                                             progress_callback=lambda index, total: progress(
                                                 0.1 + 0.85 * index / total,
                                                 desc=f"正在生成第{index + 1}/{total}段…"), **kwargs)
            torch.cuda.synchronize()
            elapsed = time.perf_counter() - started
            audio = waveform.squeeze(0).numpy()
            if not audio.size or not np.isfinite(audio).all() or np.max(np.abs(audio)) < 1e-6:
                raise RuntimeError("模型输出为空、静音或含无效数值，本次未保存音频，请查看日志。")
            OUTPUTS.mkdir(parents=True, exist_ok=True)
            stem = time.strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:8]
            path = OUTPUTS / (stem + ".wav")
            sf.write(path, audio, self.model.sample_rate, subtype="PCM_16")
            metrics = {"mode": request.mode, "characters": len(request.text), "seed": seed,
                       "segment_count": len(fragments),
                       "sample_rate": self.model.sample_rate, "audio_seconds": len(audio) / self.model.sample_rate,
                       "load_seconds": load_seconds, "generation_seconds": elapsed,
                       "peak_allocated_mib": torch.cuda.max_memory_allocated() / 1024**2,
                       "peak_reserved_mib": torch.cuda.max_memory_reserved() / 1024**2,
                       "device": torch.cuda.get_device_name(0), "torch": torch.__version__,
                       "model_path": str(MODEL_PATH), "audio_peak": float(np.max(np.abs(audio))),
                       "audio_rms": float(np.sqrt(np.mean(audio**2)))}
            metrics["real_time_factor"] = elapsed / metrics["audio_seconds"]
            path.with_suffix(".json").write_text(json.dumps({**request.__dict__, **metrics}, ensure_ascii=False, indent=2))
            torch.cuda.empty_cache()
            progress(1, desc="生成完成")
            return str(path), metrics


engine = Engine()
