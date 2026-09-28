"""
Convenience helper for local development.
Starts each FastAPI service in a subprocess.
For production-like experiments, prefer Docker Compose.
"""
import subprocess
import sys
import time

commands = [
    [sys.executable, "-m", "uvicorn", "services.auth_service:app", "--host", "127.0.0.1", "--port", "8001"],
    [sys.executable, "-m", "uvicorn", "services.policy_service:app", "--host", "127.0.0.1", "--port", "8002"],
    [sys.executable, "-m", "uvicorn", "services.resource_service:app", "--host", "127.0.0.1", "--port", "8003"],
    [sys.executable, "-m", "uvicorn", "services.gateway:app", "--host", "127.0.0.1", "--port", "8000"],
]

processes = []
try:
    for cmd in commands:
        processes.append(subprocess.Popen(cmd))
        time.sleep(1)
    print("Services started. Press Ctrl+C to stop.")
    while True:
        time.sleep(5)
except KeyboardInterrupt:
    for p in processes:
        p.terminate()
