import signal
import threading
import logging

logger = logging.getLogger(__name__)
stop_thread_event = threading.Event()

def handle_sigterm(signum, frame):
    logger.warning("⚠️ SIGTERM received, setting stop_thread_event")
    stop_thread_event.set()

def register_sigterm_handler():
    signal.signal(signal.SIGTERM, handle_sigterm)
    logger.warning("✅ SIGTERM handler registered in this worker process")