from __future__ import annotations

from pathlib import Path


DASHBOARD_APP = Path(__file__).resolve().parent / "dashboard" / "app.py"

globals_dict = {
    "__file__": str(DASHBOARD_APP),
    "__name__": "__main__",
}

exec(DASHBOARD_APP.read_text(encoding="utf-8"), globals_dict)
