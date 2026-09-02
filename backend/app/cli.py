from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.auth import normalize_email, password_hasher
from app.config import get_settings
from app.db import connect
from app.events import import_events
from app.ingestion import filter_company_rows, store_statement
from app.metrics import calculate_and_store_metrics
from app.smv.client import OPERATIONS, SmvClient


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Herramientas de datos del MVP")
    subparsers = parser.add_subparsers(dest="command", required=True)

    ingest = subparsers.add_parser("smv-ingest", help="Ingiere un estado desde la SMV")
    ingest.add_argument("--company-rpj", required=True)
    ingest.add_argument("--year", type=int, required=True)
    ingest.add_argument("--period", choices=["A", "1", "2", "3", "4"], required=True)
    ingest.add_argument("--scope", choices=["I", "C"], required=True)
    ingest.add_argument("--statement", choices=sorted(OPERATIONS), required=True)
    ingest.add_argument(
        "--reported-scale",
        choices=["unknown", "units", "thousands", "millions"],
        default="unknown",
    )
    ingest.add_argument("--scale-source-url")

    metrics = subparsers.add_parser(
        "metrics-calculate", help="Calcula y persiste metricas financieras"
    )
    metrics.add_argument("--company-rpj", required=True)
    metrics.add_argument("--year", type=int, required=True)
    metrics.add_argument("--period", choices=["A", "1", "2", "3", "4"], required=True)
    metrics.add_argument("--scope", choices=["individual", "consolidated"], default="consolidated")

    seed_user = subparsers.add_parser("seed-user", help="Crea o actualiza un usuario local")
    seed_user.add_argument("--email", required=True)
    seed_user.add_argument("--password", required=True)
    seed_user.add_argument("--name", required=True)

    events = subparsers.add_parser(
        "events-import", help="Importa metadatos curados de eventos oficiales"
    )
    events.add_argument("--file", type=Path, required=True)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.command == "smv-ingest":
        settings = get_settings()
        client = SmvClient(settings.smv_base_url, settings.smv_timeout_seconds)
        response = client.fetch_statement(
            statement_type=args.statement,
            fiscal_year=args.year,
            period_code=args.period,
            scope_code=args.scope,
        )
        rows = filter_company_rows(response.rows, args.company_rpj)

        with connect() as connection:
            result = store_statement(
                connection=connection,
                response=response,
                rows=rows,
                statement_type=args.statement,
                fiscal_year=args.year,
                period_code=args.period,
                scope_code=args.scope,
                reported_scale=args.reported_scale,
                scale_source_url=args.scale_source_url,
            )
    elif args.command == "metrics-calculate":
        with connect() as connection:
            result = calculate_and_store_metrics(
                connection=connection,
                smv_rpj=args.company_rpj,
                fiscal_year=args.year,
                period_code=args.period,
                scope=args.scope,
            )
    elif args.command == "seed-user":
        email = normalize_email(args.email)
        with connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO app_users (email, password_hash, full_name)
                VALUES (%s, %s, %s)
                ON CONFLICT (email) DO UPDATE SET
                    password_hash = EXCLUDED.password_hash,
                    full_name = EXCLUDED.full_name,
                    updated_at = NOW()
                RETURNING id, email, full_name
                """,
                (email, password_hasher.hash(args.password), args.name),
            )
            result = cursor.fetchone()
    elif args.command == "events-import":
        payload = json.loads(args.file.read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            raise ValueError("El archivo de eventos debe contener una lista JSON")
        with connect() as connection:
            result = import_events(connection, payload)
    else:
        raise RuntimeError(f"Comando no implementado: {args.command}")
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
