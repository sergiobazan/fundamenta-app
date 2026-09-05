from __future__ import annotations

import argparse
import logging
import os
import sys

from app.bootstrap import run_bootstrap
from app.cited_summaries import sync_cited_summaries
from app.config import get_settings
from app.db import connect
from app.migrations import run_migrations
from app.narrative_comparisons import sync_narrative_comparisons

logger = logging.getLogger("fundamenta.runtime")


def prepare_database(service: str) -> None:
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

    if settings.company_catalog_sync_on_start:
        try:
            from app.company_analysis import sync_company_catalog

            catalog = sync_company_catalog(settings)
            logger.info("Catálogo SMV sincronizado: %s", catalog)
        except Exception:
            logger.exception(
                "No se pudo actualizar el catálogo SMV; se conservará el catálogo existente"
            )

    if service == "api" and settings.notes_sync_in_api_on_start:
        try:
            from app.notes_worker import sync_available_jobs

            notes = sync_available_jobs()
            logger.info("Sincronización de notas al arrancar la API: %s trabajos", len(notes))
        except Exception:
            logger.exception(
                "La sincronización periódica de notas falló; la API continuará disponible"
            )

    with connect() as connection:
        summaries = sync_cited_summaries(connection)
        connection.commit()
    logger.info(
        "Resúmenes citados listos: %s creados, %s existentes",
        summaries["created"],
        summaries["unchanged"],
    )

    with connect() as connection:
        comparisons = sync_narrative_comparisons(connection)
        connection.commit()
    logger.info(
        "Comparaciones narrativas listas: %s creadas, %s existentes",
        comparisons["created"],
        comparisons["unchanged"],
    )


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Arranque de servicios de Fundamenta")
    parser.add_argument("service", choices=["api", "notes-worker"])
    args = parser.parse_args()
    prepare_database(args.service)

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
    os.environ["FUNDAMENTA_DATABASE_PREPARED"] = "1"
    os.execv(sys.executable, command)


if __name__ == "__main__":
    main()
