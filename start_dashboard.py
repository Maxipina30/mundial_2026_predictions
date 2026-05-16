from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
LOG_DIR = BASE_DIR / "logs"
STDOUT_LOG = LOG_DIR / "streamlit_stdout.log"
STDERR_LOG = LOG_DIR / "streamlit_stderr.log"

PYTHON_CANDIDATES = [
    BASE_DIR / ".runtime" / "python312" / "python.exe",
    BASE_DIR / "venv312" / "Scripts" / "python.exe",
    Path(r"C:\Users\maxip\Documents\futdata_v1\.runtime\python312\python.exe"),
    Path(sys.executable),
]


def resolve_python() -> Path:
    for candidate in PYTHON_CANDIDATES:
        if candidate.exists():
            return candidate
    return Path(sys.executable)


def launch_streamlit(python: Path, env: dict[str, str], flags: int) -> subprocess.Popen:
    return subprocess.Popen(
        [
            str(python),
            "-m",
            "streamlit",
            "run",
            "app.py",
            "--server.address",
            "127.0.0.1",
            "--server.port",
            "8501",
            "--server.headless",
            "true",
        ],
        cwd=BASE_DIR,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=flags,
    )


def main() -> int:
    LOG_DIR.mkdir(exist_ok=True)
    env = dict(os.environ)
    env["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"
    env["PYTHONIOENCODING"] = "utf-8"

    python = resolve_python()
    flags = 0
    if os.name == "nt":
        flags = (
            subprocess.CREATE_NEW_PROCESS_GROUP
            | subprocess.DETACHED_PROCESS
            | 0x01000000  # CREATE_BREAKAWAY_FROM_JOB
        )

    stdout = STDOUT_LOG.open("ab")
    stderr = STDERR_LOG.open("ab")
    try:
        process = subprocess.Popen(
            [
                str(python),
                "-m",
                "streamlit",
                "run",
                "app.py",
                "--server.address",
                "127.0.0.1",
                "--server.port",
                "8501",
                "--server.headless",
                "true",
            ],
            cwd=BASE_DIR,
            env=env,
            stdout=stdout,
            stderr=stderr,
            creationflags=flags,
        )
    except PermissionError:
        stdout.close()
        stderr.close()
        with STDERR_LOG.open("ab") as fallback_log:
            fallback_log.write(
                b"Detached process flags were blocked. Retrying without creation flags.\n"
            )
        with STDOUT_LOG.open("ab") as stdout, STDERR_LOG.open("ab") as stderr:
            process = subprocess.Popen(
                [
                    str(python),
                    "-m",
                    "streamlit",
                    "run",
                    "app.py",
                    "--server.address",
                    "127.0.0.1",
                    "--server.port",
                    "8501",
                    "--server.headless",
                    "true",
                ],
                cwd=BASE_DIR,
                env=env,
                stdout=stdout,
                stderr=stderr,
                creationflags=0,
            )
    else:
        stdout.close()
        stderr.close()
    print(f"Streamlit PID: {process.pid}")
    print("URL: http://127.0.0.1:8501/")
    print(f"Logs: {STDOUT_LOG} | {STDERR_LOG}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
