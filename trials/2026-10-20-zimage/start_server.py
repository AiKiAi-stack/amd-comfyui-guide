"""Start the workspace-owned conservative Z-Image server after a healthy probe."""
import argparse
import importlib.util
import json
import re
from datetime import datetime, timezone
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--profile",
        choices=("legacy-lowvram", "legacy-normalvram", "dynamic-nvme"),
        default="legacy-lowvram",
        help="legacy-lowvram keeps CPU text encoding; legacy-normalvram enables GPU text diagnostics.",
    )
    parser.add_argument('--ssd', action='store_true', help='Use the verified G: NVMe trial mirror with path precedence.')
    parser.add_argument('--fast-disk', action='store_true', help='Explicitly opt in to disk-backed loading; default uses ComfyUI auto policy.')
    parser.add_argument('--label', default='zimage-gpu-text', help='Separate owned server PID and logs for an isolated case.')
    args = parser.parse_args()
    assert re.fullmatch(r'[A-Za-z0-9_-]+',args.label)

    probe_path = sorted(
        (ROOT / "trials/2026-10-20-flux2-klein/gpu-probes").glob("*/result.json")
    )[-1]
    probe = json.loads(probe_path.read_text(encoding="utf-8"))
    stamp = datetime.fromisoformat(probe['completed_at']) if probe.get('completed_at') else datetime.fromtimestamp(probe_path.stat().st_mtime,timezone.utc)
    assert (
        probe["healthy"] is True
        and 0 <= (datetime.now(timezone.utc) - stamp).total_seconds() < 900
    ), "Fresh healthy GPU probe required"

    manager_path = ROOT / "trials/2026-10-19-features/manage_server.py"
    spec = importlib.util.spec_from_file_location("workspace_server_manager", manager_path)
    manager = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(manager)
    storage_args=[]
    if args.ssd:
        config=HERE/'ssd-model-paths.yaml'
        assert config.exists(), 'SSD mirror/config must be prepared first'
        storage_args=['--extra-model-paths-config',str(config)]

    if args.profile == "legacy-lowvram":
        manager.restart("zimage", cpu_text=True, extra_args=["--reserve-vram", "2.0"]+storage_args, fast_disk=args.fast_disk)
    elif args.profile == "dynamic-nvme":
        assert args.ssd, 'dynamic-nvme requires the verified SSD mirror'
        manager.restart(
            args.label, cpu_text=False,
            extra_args=['--enable-dynamic-vram', '--disable-pinned-memory',
                        '--reserve-vram', '2.0']+storage_args,
            fast_disk=True,
        )
    else:
        manager.restart(
            args.label,
            cpu_text=False,
            extra_args=[
                "--disable-dynamic-vram",
                "--reserve-vram",
                "2.0",
            ]+storage_args,
            fast_disk=args.fast_disk,
        )


if __name__ == "__main__":
    main()
