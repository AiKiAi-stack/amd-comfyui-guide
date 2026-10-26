"""Install official Docker packages after KEKE storage has been configured."""
import os
from pathlib import Path
import subprocess
import urllib.request

assert os.geteuid() == 0
assert os.path.ismount("/media/wbb/KEKE/LinuxContainers"), "Run setup-storage first"
key = Path("/etc/apt/keyrings/docker.asc")
key.parent.mkdir(exist_ok=True)
with urllib.request.urlopen("https://download.docker.com/linux/ubuntu/gpg", timeout=60) as response:
    key.write_bytes(response.read())
key.chmod(0o644)
Path("/etc/apt/sources.list.d/docker.sources").write_text("""Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: noble
Components: stable
Architectures: amd64
Signed-By: /etc/apt/keyrings/docker.asc
""")
subprocess.run(["systemctl", "daemon-reload"], check=True)
env = {**os.environ, "DEBIAN_FRONTEND": "noninteractive"}
subprocess.run(["apt-get", "update"], check=True, env=env)
subprocess.run(["apt-get", "-y", "--no-install-recommends", "-o",
                "Dir::Cache::archives=/media/wbb/KEKE/LinuxContainers/apt-cache",
                "-o", "Dpkg::Options::=--force-confold", "install", "docker-ce", "docker-ce-cli",
                "containerd.io", "docker-buildx-plugin", "docker-compose-plugin"], check=True, env=env)
subprocess.run(["systemctl", "daemon-reload"], check=True)
subprocess.run(["systemctl", "enable", "--now", "docker"], check=True)
subprocess.run(["docker", "info", "--format", "{{.DockerRootDir}} {{.Driver}}"], check=True)
