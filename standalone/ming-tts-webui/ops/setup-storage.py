"""One-time host setup: keep Docker data on a dedicated ext4 file on KEKE.

Run as root. Does not partition or format a block device.
"""
import json
import os
from pathlib import Path
import stat
import subprocess
import time

assert os.geteuid() == 0, "Run with sudo"
disk = Path("/media/wbb/KEKE")
assert subprocess.check_output(["findmnt", "-T", str(disk), "-n", "-o", "TARGET"], text=True).strip() == str(disk)
assert os.access(disk, os.W_OK), "KEKE must be writable"
source = subprocess.check_output(["findmnt", "-T", str(disk), "-n", "-o", "SOURCE"], text=True).strip()
uuid = subprocess.check_output(["blkid", "-s", "UUID", "-o", "value", source], text=True).strip()
store = disk / ".linux-containers"
store.mkdir(exist_ok=True)
image = store / "docker-store.ext4"
mount = disk / "LinuxContainers"
mount.mkdir(exist_ok=True)
if not image.exists():
    assert os.statvfs(disk).f_bavail * os.statvfs(disk).f_frsize > 60 * 1024**3, "Need at least 60 GiB free"
    with image.open("xb") as file:
        file.truncate(48 * 1024**3)
    assert stat.S_ISREG(image.stat().st_mode) and not image.is_symlink()
    subprocess.run(["mkfs.ext4", "-m", "0", "-L", "keke-containers", str(image)], check=True)
if not os.path.ismount(mount):
    subprocess.run(["mount", "-o", "loop", str(image), str(mount)], check=True)
assert subprocess.check_output(["findmnt", "-T", str(mount), "-n", "-o", "FSTYPE"], text=True).strip() == "ext4"
for name in ("docker", "containerd", "apt-cache", "backups"):
    (mount / name).mkdir(exist_ok=True)
stamp = time.strftime("%Y%m%d-%H%M%S")
fstab = Path("/etc/fstab")
old = fstab.read_text()
new = old
if not any(uuid in line and not line.lstrip().startswith("#") for line in old.splitlines()):
    new += f"\n# KEKE data disk and isolated Linux container storage\nUUID={uuid} {disk} ntfs3 defaults,nofail,uid=1000,gid=1000,iocharset=utf8,x-systemd.device-timeout=10s 0 0\n"
if str(image) not in new:
    new += f"{image} {mount} ext4 loop,nofail,x-systemd.requires-mounts-for={disk} 0 0\n"
if new != old:
    (mount / "backups" / ("fstab-" + stamp)).write_text(old)
    fstab.write_text(new)
docker_config = Path("/etc/docker/daemon.json")
docker_config.parent.mkdir(exist_ok=True)
config = json.loads(docker_config.read_text()) if docker_config.exists() else {}
if docker_config.exists():
    (mount / "backups" / ("docker-daemon-" + stamp + ".json")).write_text(docker_config.read_text())
config.update({"data-root": str(mount / "docker"), "storage-driver": "overlay2",
               "log-driver": "local", "log-opts": {"max-size": "10m", "max-file": "3"}})
config.setdefault("features", {})["containerd-snapshotter"] = False
config["proxies"] = {"http-proxy": "http://127.0.0.1:7897", "https-proxy": "http://127.0.0.1:7897", "no-proxy": "localhost,127.0.0.1,::1"}
docker_config.write_text(json.dumps(config, indent=2) + "\n")
containerd_config = Path("/etc/containerd/config.toml")
containerd_config.parent.mkdir(exist_ok=True)
assert not containerd_config.exists(), "Existing containerd config needs manual merging"
containerd_config.write_text(f'version = 2\nroot = "{mount}/containerd"\nstate = "/run/containerd"\n')
for service in ("docker", "containerd"):
    directory = Path(f"/etc/systemd/system/{service}.service.d")
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "keke-storage.conf").write_text(f"[Unit]\nRequiresMountsFor={mount}\n")
print(json.dumps({"disk": str(disk), "container_storage": str(mount), "image_file": str(image), "limit_gib": 48}, indent=2))
