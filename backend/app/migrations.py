from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from psycopg import Connection

from app.config import get_migrations_dir
from app.db import connect

MIGRATION_FILE_RE = re.compile(r"^(\d{3})_[a-z0-9_]+\.sql$")
TRANSACTION_WRAPPER_RE = re.compile(
    r"^\s*BEGIN;\s*(?P<body>.*)\s*COMMIT;\s*$",
    flags=re.DOTALL | re.IGNORECASE,
)
MIGRATION_LOCK_NAME = "fundamenta_schema_migrations"


@dataclass(frozen=True)
class Migration:
    version: int
    name: str
    path: Path
    checksum: str
    sql: str


def discover_migrations(directory: Path) -> tuple[Migration, ...]:
    if not directory.is_dir():
        raise ValueError(f"No existe el directorio de migraciones: {directory}")

    migrations: list[Migration] = []
    for path in sorted(directory.glob("*.sql")):
        match = MIGRATION_FILE_RE.fullmatch(path.name)
        if not match:
            raise ValueError(f"Nombre de migración no válido: {path.name}")
        raw_sql = path.read_text(encoding="utf-8")
        wrapper = TRANSACTION_WRAPPER_RE.fullmatch(raw_sql)
        sql = wrapper.group("body").strip() if wrapper else raw_sql.strip()
        if not sql:
            raise ValueError(f"La migración está vacía: {path.name}")
        migrations.append(
            Migration(
                version=int(match.group(1)),
                name=path.name,
                path=path,
                checksum=hashlib.sha256(raw_sql.encode("utf-8")).hexdigest(),
                sql=sql,
            )
        )

    versions = [migration.version for migration in migrations]
    if versions != list(range(1, len(migrations) + 1)):
        raise ValueError(f"La secuencia de migraciones no es continua: {versions}")
    return tuple(migrations)


def _ensure_migration_table(connection: Connection) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY CHECK (version > 0),
                name TEXT NOT NULL UNIQUE,
                checksum CHAR(64) NOT NULL,
                applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
    connection.commit()


def _applied_migrations(connection: Connection) -> dict[int, dict[str, Any]]:
    with connection.cursor() as cursor:
        cursor.execute("SELECT version, name, checksum, applied_at FROM schema_migrations")
        return {row["version"]: row for row in cursor.fetchall()}


def apply_migrations(connection: Connection, directory: Path) -> dict[str, Any]:
    migrations = discover_migrations(directory)
    _ensure_migration_table(connection)
    applied_now: list[str] = []
    skipped: list[str] = []

    with connection.cursor() as cursor:
        cursor.execute("SELECT pg_advisory_lock(hashtext(%s))", (MIGRATION_LOCK_NAME,))
    connection.commit()
    try:
        applied = _applied_migrations(connection)
        for migration in migrations:
            current = applied.get(migration.version)
            if current:
                if current["name"] != migration.name or current["checksum"] != migration.checksum:
                    raise RuntimeError(
                        f"La migración {migration.version:03d} cambió después de aplicarse"
                    )
                skipped.append(migration.name)
                continue

            try:
                with connection.cursor() as cursor:
                    cursor.execute(migration.sql)
                    cursor.execute(
                        """
                        INSERT INTO schema_migrations (version, name, checksum)
                        VALUES (%s, %s, %s)
                        """,
                        (migration.version, migration.name, migration.checksum),
                    )
                connection.commit()
            except Exception:
                connection.rollback()
                raise
            applied_now.append(migration.name)
    finally:
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_unlock(hashtext(%s))", (MIGRATION_LOCK_NAME,))
        connection.commit()

    return {
        "total": len(migrations),
        "applied": applied_now,
        "skipped": skipped,
    }


def run_migrations() -> dict[str, Any]:
    with connect() as connection:
        return apply_migrations(connection, get_migrations_dir())


def main() -> None:
    result = run_migrations()
    print(
        f"Migraciones: {result['total']} totales, "
        f"{len(result['applied'])} aplicadas, {len(result['skipped'])} existentes"
    )


if __name__ == "__main__":
    main()
