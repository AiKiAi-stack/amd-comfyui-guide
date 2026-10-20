"""Bind the completed H3 diagnostic to its actual graph and saved frames."""
from datetime import datetime
import json
from pathlib import Path
import shutil

HERE = Path(__file__).resolve().parent
TRIAL = HERE.parent / "2026-10-19-h3"
case_id, stem = "ref2va-5frame-diagnostic", "diagnostic-gpu-vae-native-reserve2"
actual = json.loads((TRIAL / f"{stem}-result.json").read_text(encoding="utf-8"))
assert actual["status"] == "success"
cases = json.loads((HERE / "cases.json").read_text(encoding="utf-8"))
case = next(c for c in cases if c["id"] == case_id)
case["runtime_profile"] = "RX6650XT；隔离H3 worktree、GGUF DynamicVRAM、4B ClipProj、GPU FP16视频VAE；--reserve-vram 2.0、同步卸载，未开启INT8 fallback。384×256、5帧、4步。433.08秒包含服务启动；仅加载诊断，不用于正常视频画质结论。"
case["evidence"] = ["../../research/h3-minimal-executable-audit.md", f"../2026-10-19-h3/{stem}-result.json"]
folder = HERE / "cases" / case_id
current = json.loads((folder / "result.json").read_text(encoding="utf-8"))
if current.get("prompt_id") == actual["prompt_id"] and current.get("status") == "success":
    raise SystemExit("Already synchronized; no changes")
archive = HERE / "attempts" / (case_id + "-before-success-" + datetime.now().strftime("%Y%m%d-%H%M%S"))
folder.resolve().relative_to((HERE / "cases").resolve())
archive.resolve().relative_to((HERE / "attempts").resolve())
archive.parent.mkdir(parents=True, exist_ok=True)
shutil.move(str(folder), str(archive))
folder.mkdir()
for suffix in ("api", "history", "submission", "process"):
    shutil.copy2(TRIAL / f"{stem}-{suffix}.json", folder / f"{suffix}.json")
record = {**case, **actual}
record["images"] = [i for i in actual["images"] if Path(i["path"]).suffix.lower() == ".png"]
record["animation"] = next(i["path"] for i in actual["images"] if Path(i["path"]).suffix.lower() == ".webp")
record["elapsed_scope"] = "server startup plus prompt execution"
(folder / "result.json").write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
(HERE / "cases.json").write_text(json.dumps(cases, ensure_ascii=False, indent=2), encoding="utf-8")
reviews = json.loads((HERE / "reviews.json").read_text(encoding="utf-8"))
reviews[case_id] = {
    "verdict": "加载、采样、解码链路通过；不是视频功能验收",
    "detail": "最新一次使用GPU FP16 VAE并预留2GB显存，实际保存5张384×256 PNG与无声WebP。首尾帧可见青色机器人、洋红围巾、方形黑眼和浅色背景，画面相似；约0.2秒不能评价动作流畅、正常时长质量或BFS角色替换。此前CPU VAE超时、INT8 VAE HIPBLAS错误及未预留显存的FP16采样OOM均保留。433.08秒包含服务启动；系统已用内存采样峰值约14.19GiB，API显存采样峰值约4.84GiB，不是所有瞬时分配的精确峰值。",
    "image": "ref2va-5frame-diagnostic-frames_00001_.png",
}
(HERE / "reviews.json").write_text(json.dumps(reviews, ensure_ascii=False, indent=2), encoding="utf-8")
blocked = json.loads((HERE / "blocked.json").read_text(encoding="utf-8"))
for item in blocked:
    if item["id"].startswith("minimax-h3"):
        detail = "独立5帧加载/采样/解码诊断已通过并保存输出，但不是本项功能的验收。本项对应的BFS/长视频/音频工作流尚无实际输出，仍未验证；不能用诊断图补位。"
        item.update(reason=detail, review={"verdict": "本功能未验证；加载诊断已通过", "detail": detail})
        item["claim_level"] = item["claim_level"].replace("缺必需模型组合，未运行", "本功能未运行；另有独立加载诊断")
(HERE / "blocked.json").write_text(json.dumps(blocked, ensure_ascii=False, indent=2), encoding="utf-8")
print("Synchronized H3 success; five frames, animation, actual graph, and prior failures retained")
