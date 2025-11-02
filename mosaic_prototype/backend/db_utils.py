from __future__ import annotations

from contextlib import contextmanager
from typing import Mapping, Sequence, Tuple

from sqlalchemy import text
from sqlalchemy.engine import Connection, Engine, Result


def _prepare_statement(sql: str, params: Sequence[object] | Mapping[str, object] | None) -> Tuple[str, dict]:
    if params is None:
        return sql, {}
    if isinstance(params, Mapping):
        return sql, dict(params)
    if not isinstance(params, Sequence):
        raise TypeError("Unsupported parameter type; expected sequence or mapping.")

    placeholders = sql.count("?")
    if placeholders != len(params):
        raise ValueError(f"Parameter count mismatch: expected {placeholders}, got {len(params)}.")

    bound_params: dict[str, object] = {}
    parts = sql.split("?")
    rebuilt = parts[0]
    for index, (part, value) in enumerate(zip(parts[1:], params)):
        key = f"p{index}"
        rebuilt += f":{key}{part}"
        bound_params[key] = value
    return rebuilt, bound_params


class SQLAlchemyConnectionWrapper:
    def __init__(self, connection: Connection):
        self._connection = connection

    def execute(
        self,
        sql: str,
        params: Sequence[object] | Mapping[str, object] | None = None,
    ) -> Result:
        statement, bound_params = _prepare_statement(sql, params)
        return self._connection.execute(text(statement), bound_params)

    def close(self) -> None:
        self._connection.close()


@contextmanager
def transactional_connection(engine: Engine) -> SQLAlchemyConnectionWrapper:
    connection = engine.connect()
    transaction = connection.begin()
    wrapper = SQLAlchemyConnectionWrapper(connection)
    try:
        yield wrapper
    except Exception:
        transaction.rollback()
        connection.close()
        raise
    else:
        transaction.commit()
        connection.close()


def connection(engine: Engine) -> SQLAlchemyConnectionWrapper:
    conn = engine.connect()
    return SQLAlchemyConnectionWrapper(conn)
