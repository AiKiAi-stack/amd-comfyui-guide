"""Preserve accepted outputs when ComfyUI rejects another output in the same prompt."""
import base64
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ReplayPartialTests(unittest.TestCase):
    def test_accepted_partial_prompt_keeps_history_and_png_but_exits_failed(self):
        png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+a0X8AAAAASUVORK5CYII=")

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def send(self, value):
                data = value if isinstance(value, bytes) else json.dumps(value).encode()
                self.send_response(200)
                self.end_headers()
                self.wfile.write(data)

            def do_POST(self):
                self.rfile.read(int(self.headers["Content-Length"]))
                self.send({"prompt_id": "accepted", "node_errors": {"bad": {"errors": ["Invalid prefix"]}}})

            def do_GET(self):
                if self.path == "/object_info":
                    self.send({"LoadImage": {}, "SaveImage": {}})
                elif self.path == "/history/accepted":
                    self.send({"accepted": {"status": {"status_str": "success"}, "outputs": {
                        "good": {"images": [{"filename": "tiny.png", "subfolder": "", "type": "output"}]}}}})
                elif self.path.startswith("/view?"):
                    self.send(png)
                else:
                    self.send({})

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        (ROOT / "runs").mkdir(exist_ok=True)
        try:
            with tempfile.TemporaryDirectory(dir=ROOT / "runs") as directory:
                directory = Path(directory)
                graph = {"input": {"class_type": "LoadImage", "inputs": {"image": "test.png"}},
                         "good": {"class_type": "SaveImage", "inputs": {"images": ["input", 0], "filename_prefix": "good"}},
                         "bad": {"class_type": "SaveImage", "inputs": {"images": ["input", 0], "filename_prefix": 123}}}
                workflow = directory / "api.json"
                workflow.write_text(json.dumps(graph), encoding="utf-8")
                out = directory / "result"
                result = subprocess.run([sys.executable, str(ROOT / "scripts/replay_workflow.py"), str(workflow),
                    "--url", f"http://127.0.0.1:{server.server_port}", "--out", str(out), "--timeout", "10"],
                    capture_output=True, timeout=20)
                self.assertEqual(result.returncode, 1)
                self.assertTrue((out / "history.json").is_file(), result.stderr.decode(errors="replace"))
                record = json.loads((out / "result.json").read_text())
                self.assertEqual(record["status"], "partial_output")
                self.assertEqual(record["execution_status"], "success")
                self.assertTrue(record["validation_errors"])
                self.assertEqual(len(record["images"]), 1)
                self.assertEqual((out / record["images"][0]["file"]).read_bytes(), png)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)


if __name__ == "__main__":
    unittest.main()
