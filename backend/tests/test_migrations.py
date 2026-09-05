from pathlib import Path

import pytest
from app.migrations import discover_migrations


def test_discovers_the_seventeen_ordered_project_migrations() -> None:
    directory = Path(__file__).resolve().parents[2] / "infra" / "postgres" / "init"

    migrations = discover_migrations(directory)

    assert [migration.version for migration in migrations] == list(range(1, 18))
    assert migrations[0].name == "001_initial_schema.sql"
    assert migrations[-1].name == "017_pacasmayo_notes_scale.sql"
    assert all(len(migration.checksum) == 64 for migration in migrations)


def test_removes_transaction_wrapper_before_execution(tmp_path: Path) -> None:
    migration_file = tmp_path / "001_example.sql"
    migration_file.write_text("BEGIN;\nCREATE TABLE example (id INT);\nCOMMIT;\n", encoding="utf-8")

    migration = discover_migrations(tmp_path)[0]

    assert migration.sql == "CREATE TABLE example (id INT);"


def test_rejects_a_gap_in_migration_versions(tmp_path: Path) -> None:
    (tmp_path / "001_first.sql").write_text("SELECT 1;", encoding="utf-8")
    (tmp_path / "003_third.sql").write_text("SELECT 3;", encoding="utf-8")

    with pytest.raises(ValueError, match="no es continua"):
        discover_migrations(tmp_path)
