import json
import sys
import time
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parents[2]
TRIAL = Path(__file__).resolve().parent
COMFY = ROOT / "ComfyUI"
BASE = "http://127.0.0.1:8188"


def graph_for(which):
    if which == "kroma":
        model = "kroma-v0.3.1-turbo-opd-Q2_K.gguf"
        encoder = "qwen3vl_4b_fp8_scaled.safetensors"
        vae = "qwen_image_vae.safetensors"
        graph = {
            "1": {"class_type": "UnetLoaderGGUF", "inputs": {"unet_name": model}},
            "2": {"class_type": "CLIPLoader", "inputs": {"clip_name": encoder, "type": "krea2", "device": "default"}},
            "3": {"class_type": "VAELoader", "inputs": {"vae_name": vae}},
            "4": {"class_type": "CLIPTextEncode", "inputs": {"text": "A little red fox sitting on a mossy rock in a misty forest, detailed fur, soft morning light, cinematic photography, no text", "clip": ["2", 0]}},
            "5": {"class_type": "ConditioningZeroOut", "inputs": {"conditioning": ["4", 0]}},
            "6": {"class_type": "EmptyLatentImage", "inputs": {"width": 512, "height": 512, "batch_size": 1}},
            "7": {"class_type": "KSampler", "inputs": {"model": ["1", 0], "positive": ["4", 0], "negative": ["5", 0], "latent_image": ["6", 0], "seed": 2106653, "steps": 4, "cfg": 1.0, "sampler_name": "euler", "scheduler": "simple", "denoise": 1.0}},
            "8": {"class_type": "VAEDecode", "inputs": {"samples": ["7", 0], "vae": ["3", 0]}},
            "9": {"class_type": "SaveImage", "inputs": {"images": ["8", 0], "filename_prefix": "Liuyue_Kroma031_Q2_4step_RX6650XT"}},
        }
    elif which in ("moss", "moss8"):
        model = "moss_image_sft_int8_convrot.safetensors"
        encoder = "qwen3.5_9b_w4a8_gptq.safetensors"
        vae = "flux2-vae_small.safetensors"
        graph = {
            "1": {"class_type": "UNETLoader", "inputs": {"unet_name": model, "weight_dtype": "default"}},
            "2": {"class_type": "CLIPLoader", "inputs": {"clip_name": encoder, "type": "moss_image", "device": "default"}},
            "3": {"class_type": "VAELoader", "inputs": {"vae_name": vae}},
            "4": {"class_type": "CLIPTextEncode", "inputs": {"text": "Astronaut walking through a dense jungle, vibrant foliage, shafts of sunlight, detailed cinematic photograph, no text", "clip": ["2", 0]}},
            "5": {"class_type": "CLIPTextEncode", "inputs": {"text": "blurry, low quality, distorted, watermark, text", "clip": ["2", 0]}},
            "6": {"class_type": "EmptyFlux2LatentImage", "inputs": {"width": 512, "height": 512, "batch_size": 1}},
            "7": {"class_type": "ModelSamplingAuraFlow", "inputs": {"model": ["1", 0], "shift": 5.0}},
            "8": {"class_type": "KSampler", "inputs": {"model": ["11", 0], "positive": ["4", 0], "negative": ["5", 0], "latent_image": ["6", 0], "seed": 2106654, "steps": 50, "cfg": 3.0, "sampler_name": "euler", "scheduler": "sgm_uniform", "denoise": 1.0}},
            "9": {"class_type": "VAEDecode", "inputs": {"samples": ["8", 0], "vae": ["3", 0]}},
            "10": {"class_type": "SaveImage", "inputs": {"images": ["9", 0], "filename_prefix": "Liuyue_MOSS_SFT_INT8_50step_RX6650XT"}},
            "11": {"class_type": "SkipLayerGuidanceDiTSimple", "inputs": {"model": ["7", 0], "double_layers": "", "single_layers": "22", "start_percent": 0.0, "end_percent": 1.0}},
        }
        if which == "moss8":
            graph["12"] = {"class_type": "LoraLoaderModelOnly", "inputs": {
                "model": ["1", 0], "lora_name": "moss-image-sft-8-steps-dmd-lora.safetensors", "strength_model": 1.0}}
            graph["7"]["inputs"]["model"] = ["12", 0]
            graph["8"]["inputs"].update(model=["7", 0], steps=8, cfg=1.0)
            del graph["11"]
            graph["10"]["inputs"]["filename_prefix"] = "Liuyue_MOSS_SFT_DMD_INT8_8step_RX6650XT"
    else:
        raise ValueError(which)
    return graph, model, encoder, vae


def main():
    which = sys.argv[1]
    graph, model, encoder, vae = graph_for(which)
    (TRIAL / f"{which}-api.json").write_text(json.dumps(graph, ensure_ascii=False, indent=2), encoding="utf-8")
    required = [COMFY / "models" / "diffusion_models" / model,
                COMFY / "models" / "text_encoders" / encoder,
                COMFY / "models" / "vae" / vae]
    if which == "moss8":
        required.append(COMFY / "models" / "loras" / "moss-image-sft-8-steps-dmd-lora.safetensors")
    deadline = time.monotonic() + 7200
    while time.monotonic() < deadline and not all(p.is_file() for p in required):
        time.sleep(15)
    if not all(p.is_file() for p in required):
        raise TimeoutError("Weights not ready: " + ", ".join(str(p) for p in required if not p.is_file()))
    deadline = time.monotonic() + 900
    while True:
        try:
            requests.get(BASE + "/queue", timeout=5).raise_for_status()
            break
        except requests.RequestException:
            if time.monotonic() >= deadline:
                raise TimeoutError("ComfyUI server did not become ready within 15 minutes")
            time.sleep(10)
    response = requests.post(BASE + "/prompt", json={"prompt": graph}, timeout=30)
    response.raise_for_status()
    submission = response.json()
    (TRIAL / f"{which}-submission.json").write_text(json.dumps(submission, indent=2), encoding="utf-8")
    if submission.get("error") or not submission.get("prompt_id"):
        raise RuntimeError(submission)
    print("SUBMITTED", submission["prompt_id"], flush=True)
    deadline = time.monotonic() + 2700
    while time.monotonic() < deadline:
        response = requests.get(BASE + "/history/" + submission["prompt_id"], timeout=30)
        response.raise_for_status()
        history = response.json().get(submission["prompt_id"])
        if history:
            (TRIAL / f"{which}-history.json").write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")
            status = history.get("status", {})
            print("DONE", json.dumps({key: status.get(key) for key in ("status_str", "completed")}), flush=True)
            for kind, details in status.get("messages", []):
                if kind == "execution_error":
                    print("ERROR", json.dumps({key: details.get(key) for key in
                          ("node_id", "node_type", "exception_type", "exception_message")}), flush=True)
            print("OUTPUTS", json.dumps(history.get("outputs")), flush=True)
            if history.get("status", {}).get("status_str") != "success":
                sys.exit(1)
            return
        time.sleep(10)
    raise TimeoutError("ComfyUI prompt did not complete within 45 minutes")


if __name__ == "__main__":
    main()
