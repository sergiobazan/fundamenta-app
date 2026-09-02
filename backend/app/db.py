from collections.abc import Iterator
from contextlib import contextmanager

import psycopg
from psycopg import Connection
from psycopg.rows import dict_row

from app.config import get_settings


def connect() -> Connection:
    return psycopg.connect(get_settings().database_url, row_factory=dict_row)


@contextmanager
def connection_scope() -> Iterator[Connection]:
    connection = connect()
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
