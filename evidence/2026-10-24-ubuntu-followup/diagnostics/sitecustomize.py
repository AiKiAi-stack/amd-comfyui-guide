"""Opt-in stack observation only; no model, memory or allocator mutation."""
import faulthandler
import signal
faulthandler.register(signal.SIGUSR1, all_threads=True)
