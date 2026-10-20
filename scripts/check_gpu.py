"""Contain native GPU initialization failures in a child process."""
import subprocess
import sys

code = '''
import torch
print('torch:', torch.__version__, 'HIP:', torch.version.hip, flush=True)
assert torch.version.hip, 'Expected AMD HIP PyTorch'
assert torch.cuda.is_available(), 'GPU is not available'
print('GPU:', torch.cuda.get_device_name(0), flush=True)
x = torch.ones((16, 16), device='cuda')
assert (x @ x).sum().item() == 4096
torch.cuda.synchronize()
print('GPU CHECK PASSED', flush=True)
'''
if __name__ == '__main__':
    try:
        result = subprocess.run([sys.executable, '-c', code], timeout=120)
        if result.returncode:
            raise SystemExit(f'GPU check failed: {result.returncode:#x}. Stop before loading models.')
    except subprocess.TimeoutExpired:
        raise SystemExit('GPU check timed out. Stop before loading models.')
