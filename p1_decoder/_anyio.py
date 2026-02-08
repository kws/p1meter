import signal
import anyio

def setup_signal_handlers():
    """Setup signal handlers for graceful shutdown."""
    def signal_handler(signum, frame):
        # Signal will be caught by KeyboardInterrupt in main_loop
        raise KeyboardInterrupt
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


def setup_scope_signal_handlers(cancel_scope: anyio.CancelScope):
    """Setup signal handlers for graceful shutdown."""
    def signal_handler(signum, frame):
        # Signal will be caught by KeyboardInterrupt in main_loop
        cancel_scope.cancel()
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)