import json
import sys
import time
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parents[2]
TRIAL = Path(__file__).resolve().parent
COMFY = ROOT / "ComfyUI"
BASE = "http://127.0.0.1:8188"
SIGMAS = "1.0, 0.978453, 0.95418, 0.926626, 0.89508, 0.845148, 0.704534, 0.414568, 0.0"


def graph_for(uncensored):
    model_name = "qwen-image-2.1-turbo-Q4_K_M.gguf"
    clip_name = (
        "Qwen-Image-2.1-Turbo-Uncensored-Q4_K.gguf"
        if uncensored else "qwen3vl_8b_w4a8.safetensors"
    )
    graph = {
        "1": {"class_type": "UnetLoaderGGUF", "inputs": {"unet_name": model_name}},
        "2": {"class_type": "CLIPLoaderGGUF" if uncensored else "CLIPLoader", "inputs": {
            "clip_name": clip_name, "type": "qwen_image",
            **({} if uncensored else {"device": "default"})}},
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": "qwen_image_2.1_vae_bf16.safetensors"}},
        "4": {"class_type": "TextEncodeQwenImage21", "inputs": {
            "clip": ["2", 0], "vae": ["3", 0], "resolution": 512,
            "prompt": "A fluffy white cat in a rain-soaked Shanghai cafe, looking out at neon reflections. Cinematic photorealism, warm indoor light, no text.",
            "negative_prompt": "blur, low quality, anatomy errors, text, watermark"}},
        "5": {"class_type": "CFGGuider", "inputs": {
            "model": ["1", 0], "positive": ["4", 0], "negative": ["4", 1], "cfg": 1.0}},
        "6": {"class_type": "ManualSigmas", "inputs": {"sigmas": SIGMAS}},
        "7": {"class_type": "KSamplerSelect", "inputs": {"sampler_name": "euler"}},
        "8": {"class_type": "RandomNoise", "inputs": {"noise_seed": 2106652}},
        "9": {"class_type": "SamplerCustomAdvanced", "inputs": {
            "noise": ["8", 0], "guider": ["5", 0], "sampler": ["7", 0],
            "sigmas": ["6", 0], "latent_image": ["4", 2]}},
        "10": {"class_type": "VAEDecode", "inputs": {"samples": ["9", 0], "vae": ["3", 0]}},
        "11": {"class_type": "SaveImage", "inputs": {
            "images": ["10", 0], "filename_prefix": "Liuyue_Qwen21_Turbo_UN_RX6650XT" if uncensored else "Liuyue_Qwen21_Turbo_RX6650XT"}},
    }
    return graph, model_name, clip_name


def main():
    uncensored = len(sys.argv) > 1 and sys.argv[1] == "uncensored"
    label = "qwen-turbo-un" if uncensored else "qwen-turbo"
    graph, model_name, clip_name = graph_for(uncensored)
    (TRIAL / f"{label}-api.json").write_text(json.dumps(graph, ensure_ascii=False, indent=2), encoding="utf-8")
    model = COMFY / "models" / "diffusion_models" / model_name
    clip = COMFY / "models" / "text_encoders" / clip_name
    mmproj = COMFY / "models" / "text_encoders" / "mmproj-Qwen-Image-2.1-Turbo-Uncensored-F16.gguf"
    required = [model, clip] + ([mmproj] if uncensored else [])
    deadline = time.monotonic() + 7200
    while time.monotonic() < deadline and not all(p.is_file() for p in required):
        time.sleep(15)
    if not all(p.is_file() for p in required):
        raise TimeoutError("Weights not ready: " + ", ".join(str(p) for p in required if not p.is_file()))

    response = requests.post(BASE + "/prompt", json={"prompt": graph}, timeout=30)
    response.raise_for_status()
    submission = response.json()
    (TRIAL / f"{label}-submission.json").write_text(json.dumps(submission, indent=2), encoding="utf-8")
    if submission.get("error") or not submission.get("prompt_id"):
        raise RuntimeError(submission)
    print("SUBMITTED", submission["prompt_id"], flush=True)
    deadline = time.monotonic() + 1800
    while time.monotonic() < deadline:
        response = requests.get(BASE + "/history/" + submission["prompt_id"], timeout=30)
        response.raise_for_status()
        history = response.json().get(submission["prompt_id"])
        if history:
            (TRIAL / f"{label}-history.json").write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")
            print("DONE", json.dumps(history.get("status")), flush=True)
            print("OUTPUTS", json.dumps(history.get("outputs")), flush=True)
            if history.get("status", {}).get("status_str") != "success":
                sys.exit(1)
            return
        time.sleep(10)
    raise TimeoutError("ComfyUI prompt did not complete within 30 minutes")


if __name__ == "__main__":
    main()
