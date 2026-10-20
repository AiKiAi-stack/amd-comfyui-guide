"""Restore the existing localhost-only report preview without touching ComfyUI."""
import subprocess
import sys
import time
from pathlib import Path
import requests

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
url='http://127.0.0.1:8767/trials/2026-10-19-features/feature-report.html'
try:
    response=requests.get(url,timeout=3)
    response.raise_for_status()
    print('REPORT_SERVER_READY_EXISTING',url)
except requests.ConnectionError:
    with (HERE/'report-server.log').open('ab') as log:
        process=subprocess.Popen([sys.executable,'-m','http.server','8767','--bind','127.0.0.1','--directory',str(ROOT)],cwd=ROOT,
                                 stdout=log,stderr=log,creationflags=subprocess.CREATE_NO_WINDOW)
    (HERE/'report-server.pid').write_text(str(process.pid),encoding='utf-8')
    for _ in range(20):
        if process.poll() is not None: raise RuntimeError('Preview server exited; inspect report-server.log')
        try:
            requests.get(url,timeout=2).raise_for_status()
            print('REPORT_SERVER_READY',process.pid,url)
            break
        except requests.ConnectionError: time.sleep(0.5)
    else: raise RuntimeError('Report server readiness timeout')
