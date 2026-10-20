"""Serve the offline report on loopback for the in-app browser."""
from pathlib import Path
import socket
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
for port in range(8766, 8771):
    with socket.socket() as sock:
        if sock.connect_ex(("127.0.0.1", port)) == 0:
            continue
    with (HERE / "preview-server.log").open("ab") as log:
        process = subprocess.Popen(
            [sys.executable, "-m", "http.server", str(port), "--bind", "127.0.0.1", "--directory", str(ROOT)],
            cwd=ROOT, stdout=log, stderr=log, creationflags=subprocess.CREATE_NO_WINDOW,
        )
    (HERE / "preview-server.pid").write_text(str(process.pid))
    url = f"http://127.0.0.1:{port}/trials/2026-10-19-features/feature-report.html"
    (HERE / "preview-url.txt").write_text(url)
    print(url, flush=True)
    break
else:
    raise RuntimeError("No free loopback preview port")
