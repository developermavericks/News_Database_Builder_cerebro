import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
env_local = os.path.join(os.path.dirname(__file__), ".env.local")
if os.path.exists(env_local):
    # Keep container/OS env precedence over local file values.
    load_dotenv(env_local, override=False)

# --- Hardware Profiles ---
# Set HARDWARE_PROFILE to "16GB" or "64GB" in your .env.local
HARDWARE_PROFILE = os.getenv("HARDWARE_PROFILE", "16GB")

PROFILES = {
    "16GB": {
        "CELERY_CONCURRENCY": 20,
        "DB_POOL_SIZE": 10,
        "DB_MAX_OVERFLOW": 15,
        "BROWSER_POOL_SIZE": 8,
        "OLLAMA_MAX_WORKERS": 1,
        "TASK_TIME_LIMIT": 180,        # 3 minutes
        "TASK_SOFT_TIME_LIMIT": 150,   # 2.5 minutes
        "WORKER_MAX_MEMORY": 400_000,  # 400MB (in KB for Celery)
    },
    "64GB": {
        "CELERY_CONCURRENCY": 50,
        "DB_POOL_SIZE": 80,
        "DB_MAX_OVERFLOW": 120,
        "BROWSER_POOL_SIZE": 10,
        "OLLAMA_MAX_WORKERS": 4,
        "TASK_TIME_LIMIT": 1800,       # 30 minutes (Docker stability for long scrape bursts)
        "TASK_SOFT_TIME_LIMIT": 1500,  # 25 minutes
        "WORKER_MAX_MEMORY": 1_500_000, # 1.5GB — safe on 64GB system
    }
}

# Fallback to 16GB if unknown profile
CURRENT_PROFILE = PROFILES.get(HARDWARE_PROFILE, PROFILES["16GB"])

import threading
import asyncio

# --- Sync-to-Async Bridge ---
# Allows gevent/sync tasks to call persistent async components (BrowserPool)
if os.name == 'nt':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

_loop = asyncio.new_event_loop()
def _start_async_loop(loop):
    asyncio.set_event_loop(loop)
    loop.run_forever()

_loop_thread = threading.Thread(target=_start_async_loop, args=(_loop,), daemon=True)
_loop_thread.start()

def run_async(coro, timeout: float | None = None):
    """Bridge: Run an async coroutine on the background thread and wait for result.

    `timeout` is seconds; when hit, a TimeoutError is raised to avoid deadlocking Celery workers.
    """
    future = asyncio.run_coroutine_threadsafe(coro, _loop)
    try:
        return future.result(timeout=timeout)
    except Exception:
        # Best-effort cancel to free the event loop.
        try:
            future.cancel()
        except Exception:
            pass
        raise

print(f"NEXUS: Loaded Hardware Profile: {HARDWARE_PROFILE}")
