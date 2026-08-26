from __future__ import annotations

import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parent
SHUTDOWN_TIMEOUT_SECONDS = 5


def backend_python() -> str:
    candidates = (
        ROOT / "backend" / ".venv" / "bin" / "python",
        ROOT / "backend" / ".venv" / "Scripts" / "python.exe",
    )
    return str(next((path for path in candidates if path.is_file()), Path(sys.executable)))


def npm_command() -> str:
    executable = "npm.cmd" if os.name == "nt" else "npm"
    command = shutil.which(executable)
    if command is None:
        raise RuntimeError("npm was not found. Install Node.js and npm before starting Cowriter.")
    return command


def start_process(label: str, command: list[str]) -> subprocess.Popen[bytes]:
    print(f"Starting {label}: {' '.join(command)}", flush=True)
    if os.name == "nt":
        return subprocess.Popen(
            command,
            cwd=ROOT,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
        )
    return subprocess.Popen(command, cwd=ROOT, start_new_session=True)


def stop_process(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return
    try:
        if os.name == "nt":
            process.terminate()
        else:
            os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        return


def kill_process(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return
    try:
        if os.name == "nt":
            process.kill()
        else:
            os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        return


def shutdown(processes: list[subprocess.Popen[bytes]]) -> None:
    for process in processes:
        stop_process(process)

    deadline = time.monotonic() + SHUTDOWN_TIMEOUT_SECONDS
    while time.monotonic() < deadline and any(process.poll() is None for process in processes):
        time.sleep(0.1)

    for process in processes:
        kill_process(process)


def main() -> int:
    processes: list[tuple[str, subprocess.Popen[bytes]]] = []
    try:
        processes.append((
            "backend",
            start_process("backend", [backend_python(), str(ROOT / "backend" / "app.py")]),
        ))
        processes.append((
            "frontend",
            start_process("frontend", [npm_command(), "run", "dev", "--prefix", "frontend"]),
        ))
        print("Cowriter is available at http://127.0.0.1:5173", flush=True)
        print("Press Ctrl+C to stop both services.", flush=True)

        while True:
            for label, process in processes:
                return_code = process.poll()
                if return_code is not None:
                    print(f"{label.capitalize()} exited with status {return_code}.", file=sys.stderr)
                    return return_code
            time.sleep(0.25)
    except KeyboardInterrupt:
        print("\nStopping Cowriter...", flush=True)
        return 0
    except (OSError, RuntimeError) as error:
        print(f"Could not start Cowriter: {error}", file=sys.stderr)
        return 1
    finally:
        shutdown([process for _, process in processes])


if __name__ == "__main__":
    raise SystemExit(main())
