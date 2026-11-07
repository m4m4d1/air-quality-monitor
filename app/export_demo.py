"""Export a static snapshot of the API for the GitHub Pages demo.

    python -m app.export_demo        # writes web/data/demo.json

The dashboard reads this file when no API is available, so the same web/
folder works both behind the FastAPI server and as a static site.
"""
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from fastapi.testclient import TestClient

from . import config, ispu, simulator

OUT = Path(__file__).resolve().parent.parent / "web" / "data" / "demo.json"


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        config.DB_PATH = Path(tmp) / "demo.db"
        os.environ["AQ_SIMULATE"] = "0"
        simulator.backfill(hours=72 + ispu.MAX_HOURS)
        from .main import app

        paths = ["stations", "summary", "alerts?hours=24&min_category=unhealthy"]
        paths += [f"stations/{s['id']}/readings?hours=72" for s in config.STATIONS]
        with TestClient(app) as client:
            api = {p: client.get(f"/api/{p}").json() for p in paths}

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                               "api": api}, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {OUT} ({OUT.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
