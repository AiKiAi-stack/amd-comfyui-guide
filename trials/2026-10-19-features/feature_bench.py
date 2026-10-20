import argparse
import copy
import importlib.util
import json
import shutil
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
PREVIOUS = ROOT / "trials" / "2026-10-18"
COMFY = ROOT / "ComfyUI"
BASE = "http://127.0.0.1:8188"


def old_module():
    spec = importlib.util.spec_from_file_location("old_trials", PREVIOUS / "run_image_model.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def node(kind, **inputs):
    return {"class_type": kind, "inputs": inputs}


def source(name):
    files = {
        "cat": "QwenImage21_RX6650XT_768_00001_.png",
        "fox": "Liuyue_Kroma031_Q2_4step_RX6650XT_00001_.png",
        "astronaut": "Liuyue_MOSS_SFT_DMD_INT8_8step_RX6650XT_00001_.png",
    }
    src = COMFY / "output" / files[name]
    dest = COMFY / "input" / "featurebench" / f"{name}.png"
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    return "featurebench/" + dest.name


def add_input(graph, name, index=30):
    graph[str(index)] = node("LoadImage", image=name)
    graph[str(index + 1)] = node("ImageScale", image=[str(index), 0], upscale_method="lanczos", width=512, height=512, crop="disabled")
    return [str(index + 1), 0]


def moss_graph(case):
    graph = copy.deepcopy(old_module().graph_for("moss8")[0])
    graph["4"]["inputs"]["text"] = case["prompt"]
    graph["5"]["inputs"]["text"] = "blurry, distorted, watermark"
    graph["8"]["inputs"]["seed"] = case.get("seed", 66501001)
    graph["10"]["inputs"]["filename_prefix"] = "FeatureBench/" + case["id"]
    if case["recipe"] == "img2img":
        image = add_input(graph, source("astronaut"))
        graph["32"] = node("VAEEncode", pixels=image, vae=["3", 0])
        graph["8"]["inputs"].update(latent_image=["32", 0], denoise=0.6)
    return graph


def kroma_graph(case):
    graph = copy.deepcopy(old_module().graph_for("kroma")[0])
    graph["4"]["inputs"]["text"] = case["prompt"]
    graph["7"]["inputs"]["seed"] = case.get("seed", 66502001)
    graph["9"]["inputs"]["filename_prefix"] = "FeatureBench/" + case["id"]
    if case["recipe"] == "img2img":
        image = add_input(graph, source("cat"))
        graph["32"] = node("VAEEncode", pixels=image, vae=["3", 0])
        graph["7"]["inputs"].update(latent_image=["32", 0], denoise=0.6)
    elif case["recipe"] == "reference":
        inputs = {"clip": ["2", 0], "vae": ["3", 0], "prompt": case["prompt"]}
        reference_images = []
        for i, filename in enumerate(case["refs"], 1):
            ref = add_input(graph, filename, 30 + 3 * (i - 1))
            inputs[f"image{i}"] = ref
            reference_images.append(ref)
        if case.get("reference_vae_resolution") == 512:
            # Preserve EditPlus' original 384-pixel vision path, but supply
            # native 512 VAE references separately to fit the 8GB GPU.
            inputs.pop("vae")
        graph["40"] = {"class_type": "TextEncodeQwenImageEditPlus", "inputs": inputs}
        conditioning = ["40", 0]
        if case.get("reference_vae_resolution") == 512:
            for i, ref in enumerate(reference_images):
                encode_id, attach_id = str(100 + i), str(120 + i)
                graph[encode_id] = node("VAEEncode", pixels=ref, vae=["3", 0])
                graph[attach_id] = node("ReferenceLatent", conditioning=conditioning, latent=[encode_id, 0])
                conditioning = [attach_id, 0]
        graph["41"] = node("FluxKontextMultiReferenceLatentMethod", conditioning=conditioning, reference_latents_method="index_timestep_zero")
        graph["7"]["inputs"]["positive"] = ["41", 0]
        graph["5"]["inputs"]["conditioning"] = ["41", 0]
    return graph


def qwen_graph(case):
    graph = json.loads((PREVIOUS / "qwen-base-edit-512-api.json").read_text(encoding="utf-8"))
    graph.pop("8", None)
    graph["4"]["inputs"].pop("images.image_1", None)
    graph["4"]["inputs"].update(prompt=case["prompt"], negative_prompt="blurry, distorted, watermark", resolution=512)
    graph["5"]["inputs"]["seed"] = case.get("seed", 66503001)
    graph["7"]["inputs"]["filename_prefix"] = "FeatureBench/" + case["id"]
    if case.get("lora"):
        graph["80"] = node("LoraLoaderModelOnly", model=["1", 0], lora_name=case["lora"]["name"], strength_model=case["lora"].get("strength", 1.0))
        graph["5"]["inputs"]["model"] = ["80", 0]
    for i, filename in enumerate(case.get("refs", []), 1):
        idx = 30 + (i - 1) * 3
        image = add_input(graph, filename, idx)
        graph["4"]["inputs"][f"images.image_{i}"] = image
    if case["recipe"] == "inpaint":
        image = ["31", 0]
        graph["50"] = node("SolidMask", value=0.0, width=512, height=512)
        graph["51"] = node("SolidMask", value=1.0, width=230, height=300)
        graph["52"] = node("FeatherMask", mask=["51", 0], left=12, top=12, right=12, bottom=12)
        graph["53"] = node("MaskComposite", destination=["50", 0], source=["52", 0], x=250, y=200, operation="add")
        graph["54"] = node("VAEEncode", pixels=image, vae=["3", 0])
        graph["55"] = node("SetLatentNoiseMask", samples=["54", 0], mask=["53", 0])
        graph["5"]["inputs"]["latent_image"] = ["55", 0]
        graph["56"] = node("ImageCompositeMasked", destination=image, source=["6", 0], x=0, y=0, resize_source=False, mask=["53", 0])
        graph["7"]["inputs"]["images"] = ["56", 0]
        graph["57"] = node("MaskToImage", mask=["53", 0])
        graph["58"] = node("SaveImage", images=["57", 0], filename_prefix="FeatureBench/" + case["id"] + "-mask")
        graph["59"] = node("SaveImage", images=image, filename_prefix="FeatureBench/" + case["id"] + "-input")
    elif case["recipe"] == "caption":
        graph["40"] = node("TextGenerate", clip=["2", 0], image=["31", 0], prompt="Describe this image as one concise English image generation prompt. Include the subject, setting, lighting and composition. Output only the prompt.", max_length=160, sampling_mode="off", thinking=False, use_default_template=True, mtp="off")
        graph["4"]["inputs"]["prompt"] = ["40", 0]
        graph["4"]["inputs"].pop("images.image_1", None)
        graph["41"] = node("PreviewAny", source=["40", 0])
    if case.get("qwen_cache_device"):
        graph["81"] = node("QwenImage21Cache", model=graph["5"]["inputs"]["model"], device=case["qwen_cache_device"], dtype="default")
        graph["5"]["inputs"]["model"] = ["81", 0]
    return graph


def turbo_un_graph(case):
    graph = qwen_graph(case)
    sampler = graph.pop("5")["inputs"]
    graph["1"]["inputs"]["unet_name"] = "qwen-image-2.1-turbo-Q4_K_M.gguf"
    graph["2"] = node("CLIPLoaderGGUF", clip_name="Qwen-Image-2.1-Turbo-Uncensored-Q4_K.gguf", type="qwen_image")
    graph["60"] = node("CFGGuider", model=sampler["model"], positive=["4", 0], negative=["4", 1], cfg=1.0)
    graph["61"] = node("ManualSigmas", sigmas="1.0, 0.978453, 0.95418, 0.926626, 0.89508, 0.845148, 0.704534, 0.414568, 0.0")
    graph["62"] = node("KSamplerSelect", sampler_name="euler")
    graph["63"] = node("RandomNoise", noise_seed=sampler["seed"])
    graph["64"] = node("SamplerCustomAdvanced", noise=["63", 0], guider=["60", 0], sampler=["62", 0], sigmas=["61", 0], latent_image=sampler["latent_image"])
    graph["6"]["inputs"]["samples"] = ["64", 0]
    return graph


def run(case):
    case_dir = HERE / "cases" / case["id"]
    case_dir.mkdir(parents=True, exist_ok=True)
    result_path = case_dir / "result.json"
    if result_path.exists():
        print("EXISTS", case["id"], flush=True)
        return
    graph = {"moss": moss_graph, "kroma": kroma_graph, "qwen": qwen_graph, "turbo-un": turbo_un_graph}[case["model"]](case)
    (case_dir / "api.json").write_text(json.dumps(graph, ensure_ascii=False, indent=2), encoding="utf-8")
    started = time.time()
    result = {**case, "started_at": started, "review": "pending"}
    try:
        response = requests.post(BASE + "/prompt", json={"prompt": graph}, timeout=60)
        submission = response.json()
        (case_dir / "submission.json").write_text(json.dumps(submission, ensure_ascii=False, indent=2), encoding="utf-8")
        response.raise_for_status()
        prompt_id = submission["prompt_id"]
        result["prompt_id"] = prompt_id
        print("SUBMITTED", case["id"], prompt_id, flush=True)
        deadline = time.monotonic() + 2400
        while time.monotonic() < deadline:
            try:
                history = requests.get(BASE + "/history/" + prompt_id, timeout=30).json().get(prompt_id)
            except requests.ReadTimeout:
                # A busy local server can temporarily stop answering during GPU work.
                continue
            if history:
                (case_dir / "history.json").write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")
                result["status"] = history["status"]["status_str"]
                result["images"] = []
                result["text_outputs"] = []
                for output in history.get("outputs", {}).values():
                    result["text_outputs"].extend(output.get("text", []))
                    for item in output.get("images", []):
                        path = COMFY / "output" / item.get("subfolder", "") / item["filename"]
                        result["images"].append(str(path))
                result["errors"] = [{k: details.get(k) for k in ("node_type", "exception_type", "exception_message")} for kind, details in history["status"].get("messages", []) if kind == "execution_error"]
                if result["status"] == "success" and result["images"]:
                    shutil.copy2(result["images"][0], COMFY / "input" / "featurebench" / (case["id"] + ".png"))
                break
            time.sleep(5)
        else:
            result["status"] = "timeout"
    except Exception as error:
        result.update(status="runner_error", error=str(error))
    result["elapsed_seconds"] = round(time.time() - started, 2)
    result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print("DONE", case["id"], result["status"], result["elapsed_seconds"], flush=True)
    if result["status"] == "runner_error":
        raise RuntimeError("Stopping batch after server/transport failure; preserve evidence and restart before retry")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("model", choices=["moss", "kroma", "qwen", "turbo-un"])
    parser.add_argument("--case")
    args = parser.parse_args()
    source("cat")
    source("fox")
    source("astronaut")
    cases = json.loads((HERE / "cases.json").read_text(encoding="utf-8"))
    for case in cases:
        if case["model"] == args.model and (args.case is None or case["id"] == args.case):
            run(case)
