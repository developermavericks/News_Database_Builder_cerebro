import subprocess
import sys
import io
import os
import time
import socket
import logging

# Set standard IO to unbuffered or ensure flush for Windows live logs
import os
os.environ['PYTHONUNBUFFERED'] = '1'

# Basic logging for the orchestrator
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("ORCHESTRATOR")

def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

def check_redis():
    """Check if Redis is running on default port 6379."""
    try:
        with socket.create_connection(("localhost", 6379), timeout=1):
            return True
    except:
        return False

def start_redis_docker():
    """Attempt to start Redis via Docker if not running."""
    logger.info("Redis not detected. Attempting to start via Docker...")
    try:
        subprocess.run(["docker", "run", "-d", "--name", "nexus-redis-local", "-p", "6379:6379", "redis:7-alpine"], 
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(2)
        return check_redis()
    except:
        return False

def cleanup_zombies():
    """Kill any orphaned processes associated with this project (Python, Celery, Vite)."""
    logger.info("Cleaning up existing processes...")
    if os.name == 'nt':
        try:
            # 1. Kill processes holding project ports (Vite/Backend)
            for port in [8000, 5173]:
                subprocess.run(['powershell', '-Command', 
                               f'Stop-Process -Id (Get-NetTCPConnection -LocalPort {port}).OwningProcess -Force'], 
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            # 2. Kill project processes by command line signature
            subprocess.run(['wmic', 'process', 'where', "commandline like '%celery%' or commandline like '%run_backend%'", 'call', 'terminate'], 
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            time.sleep(2) # Give it a moment to clear Redis connections
        except Exception as e:
            logger.warning(f"Cleanup routine warning: {e}")
    return True

def main():
    print("\n" + "="*50, flush=True)
    print(" [NEXUS] - Global News Intelligence Orchestrator", flush=True)
    print(" " + "="*50 + "\n", flush=True)

    cleanup_zombies()

    base_dir = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.join(base_dir, "backend")
    frontend_dir = os.path.join(base_dir, "frontend")
    
    python_exe = os.path.join(backend_dir, "venv", "Scripts", "python.exe")
    npx_exe = "npx.cmd" if os.name == 'nt' else "npx"

    if not os.path.exists(python_exe):
        python_exe = "python"
        logger.warning("Virtual environment not found, using global python.")

    # Load .env variables
    env = os.environ.copy()
    env_file = os.path.join(backend_dir, ".env")
    if os.path.exists(env_file):
        with open(env_file, "r") as f:
            for line in f:
                if "=" in line and not line.startswith("#"):
                    k, v = line.strip().split("=", 1)
                    env[k.strip()] = v.strip()

    # 1. Check Dependencies
    if not check_redis():
        if not start_redis_docker():
            logger.error("Redis is required but not running. Please start Redis or Docker Desktop.")
            sys.exit(1)
    logger.info("[OK] Redis Connection Verified.")

    # 2. Port Cleanup
    for port in [8000, 5173]:
        if is_port_in_use(port):
            logger.warning(f"Port {port} is already in use. Attempting to proceed anyway...")

    processes = []
    logs = []

    def start_service(name, cmd, cwd, log_file):
        logger.info(f"Starting {name}...")
        f = open(os.path.join(base_dir, log_file), "a", encoding="utf-8")
        proc = subprocess.Popen(
            cmd, cwd=cwd, env=env, stdout=f, stderr=subprocess.STDOUT, shell=(os.name == 'nt' and not cmd[0].endswith('.exe'))
        )
        processes.append((name, proc, f))
        return proc

    try:
        # Start API
        start_service("Backend API", [python_exe, "run_backend.py"], backend_dir, "api.log")
        
        # Optimization: Split into 'Management' and 'Processing' tiers
        hw_profile = env.get("HARDWARE_PROFILE", "16GB")
        
        # Windows-Specific Stability: Gevent + Playwright is unstable on NT.
        # We use 'solo' pool but scale worker count instead of internal concurrency.
        is_windows = os.name == 'nt'
        pool_type = "solo" if is_windows else ("gevent" if hw_profile == "64GB" else "solo")
        
        # Scaling Strategy: On 64GB Windows, we spawn 20 workers (2 Management + 18 Article Processors).
        if is_windows:
            num_workers = 20 if hw_profile == "64GB" else 4
            concurrency = 1
        else:
            num_workers = 6 if hw_profile == "64GB" else 1
            concurrency = 50 if hw_profile == "64GB" else 1
        
        for i in range(1, num_workers + 1):
            if i <= 2: # Priority Management Workers (STRICTLY LIMITS to 2 concurrent jobs)
                queues = "priority"
                worker_concurrency = 1
                logger.info(f"Starting Management Worker #{i} (Dedicated to Job Control)...")
            else: # Bulk Scraping Workers (Dedicated to Article Extraction)
                queues = "celery"
                worker_concurrency = 1
                logger.info(f"Starting Processing Worker #{i} (Dedicated to Articles)...")

            start_service(f"Celery Worker #{i}", [
                python_exe, "-m", "celery", "-A", "celery_app", "worker", 
                "--loglevel=info", "-P", pool_type, "-c", str(worker_concurrency),
                "-Q", queues,
                "--prefetch-multiplier=1", "-n", f"worker{i}@{queues}_node"
            ], backend_dir, f"worker{i}.log")
        
        # Start Beat (Scheduler)
        start_service("Celery Beat", [python_exe, "-m", "celery", "-A", "celery_app", "beat", "--loglevel=info"], backend_dir, "beat.log")
        
        # Start Flower (Visual Pipeline Monitor)
        logger.info("Starting Visual Pipeline Monitor (Flower) on http://localhost:5555...")
        start_service("Flower Monitor", [python_exe, "-m", "celery", "-A", "celery_app", "flower", "--port=5555"], backend_dir, "flower.log")
        
        # Start Frontend
        start_service("Frontend (Vite)", [npx_exe, "vite", "--port", "5173", "--host"], frontend_dir, "frontend.log")
        
        logger.info("\n" + "="*50)
        logger.info("        --- All services initialized! ---         ")
        logger.info("-"*50)
        logger.info(" - Dashboard:  http://localhost:5173")
        logger.info(" - API Docs:   http://localhost:8000/docs")
        logger.info(" - Pipeline Viz: http://localhost:5555 (Flower)")
        logger.info("-"*50)
        logger.info(" Logs available in root directory: api.log, worker.log, beat.log, frontend.log")
        logger.info(" Press Ctrl+C to shutdown all services safely.")

        while True:
            time.sleep(5)
            for name, proc, _ in processes:
                if proc.poll() is not None:
                    logger.error(f"Critical service '{name}' has stopped (Exit code: {proc.returncode}).")
                    raise KeyboardInterrupt

    except KeyboardInterrupt:
        logger.info("Shutting down services...")
    finally:
        for name, proc, f in processes:
            logger.info(f"Stopping {name}...")
            if os.name == 'nt':
                subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                proc.terminate()
            f.close()
        logger.info("Full system shutdown complete.")

if __name__ == "__main__":
    main()
