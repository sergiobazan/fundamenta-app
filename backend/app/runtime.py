from __future__ import annotations

import argparse
import logging
import os
import sys

from app.bootstrap import run_bootstrap
from app.config import get_settings
from app.migrations import run_migrations

logger = logging.getLogger("fundamenta.runtime")


def prepare_database() -> None:
    settings = get_settings()
    if settings.bootstrap_on_start:
        result = run_bootstrap()
        logger.info("Inicialización de datos: %s", result["status"])
    else:
        result = run_migrations()
        logger.info(
            "Migraciones listas: %s aplicadas, %s existentes",
            len(result["applied"]),
            len(result["skipped"]),
        )


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Arranque de servicios de Fundamenta")
    parser.add_argument("service", choices=["api", "notes-worker"])
    args = parser.parse_args()
    prepare_database()

    if args.service == "api":
        port = os.environ.get("PORT", "8000")
        command = [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "0.0.0.0",
            "--port",
            port,
            "--proxy-headers",
            "--forwarded-allow-ips=*",
        ]
    else:
        command = [sys.executable, "-m", "app.notes_worker"]
    os.execv(sys.executable, command)


if __name__ == "__main__":
    main()
