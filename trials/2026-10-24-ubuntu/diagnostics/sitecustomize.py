"""Opt-in diagnostics; no patch to ComfyUI or Torch."""
import ctypes
import faulthandler
import gc
import json
import os
import signal
import sys
import time

faulthandler.register(signal.SIGUSR1, all_threads=True)

def trim_host_heap(signum, frame):
    import psutil
    process = psutil.Process()
    before = process.memory_info().rss
    gc.collect()
    result = ctypes.CDLL(None).malloc_trim(0)
    after = process.memory_info().rss
    management = sys.modules.get('comfy.model_management')
    print('HOST_HEAP_TRIM ' + json.dumps({'time': time.time(), 'pid': os.getpid(),
        'before_rss': before, 'after_rss': after, 'rss_reduction': before-after,
        'malloc_trim_result': result, 'available_bytes': psutil.virtual_memory().available,
        'registered_pinned_bytes': getattr(management, 'TOTAL_PINNED_MEMORY', None)}), flush=True)

signal.signal(signal.SIGUSR2, trim_host_heap)
