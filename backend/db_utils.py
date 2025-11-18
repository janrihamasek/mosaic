from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator, Mapping, Optional, Sequence, Tuple, cast

from sqlalchemy import text
from sqlalchemy.engine import Connection, Engine, Result, RowMapping


def _prepare_statement(
    sql: str, params: Sequence[object] | Mapping[str, object] | None
) -> Tuple[str, dict]:
    if params is None:
        return sql, {}
    if isinstance(params, Mapping):
        return sql, dict(params)
    if not isinstance(params, Sequence):
        raise TypeError("Unsupported parameter type; expected sequence or mapping.")

    placeholders = sql.count("?")
    if placeholders != len(params):
        raise ValueError(
            f"Parameter count mismatch: expected {placeholders}, got {len(params)}."
        )

    bound_params: dict[str, object] = {}
    parts = sql.split("?")
    rebuilt = parts[0]
    for index, (part, value) in enumerate(zip(parts[1:], params)):
        key = f"p{index}"
        rebuilt += f":{key}{part}"
        bound_params[key] = value
    return rebuilt, bound_params


class ResultWrapper:
    def __init__(self, result: Result):
        self._result = result

    def fetchone(self) -> Optional[Mapping[str, object]]:
        row = self._result.fetchone()
        return None if row is None else cast(Mapping[str, object], row._mapping)

    def fetchall(self) -> list[Mapping[str, object]]:
        return [
            cast(Mapping[str, object], row._mapping) for row in self._result.fetchall()
        ]

    def first(self) -> Optional[Mapping[str, object]]:
        row = self._result.first()
        return None if row is None else cast(Mapping[str, object], row._mapping)

    def mappings(self):
        return self._result.mappings()

    def scalar(self):
        return self._result.scalar()

    def scalar_one(self):
        return self._result.scalar_one()

    def scalar_one_or_none(self):
        return self._result.scalar_one_or_none()

    def scalars(self):
        return self._result.scalars()

    @property
    def rowcount(self) -> int:
        raw = getattr(self._result, "rowcount", None)
        return int(raw or 0)


class SQLAlchemyConnectionWrapper:
    def __init__(self, connection: Connection):
        self._connection = connection

    def execute(
        self,
        sql: str,
        params: Sequence[object] | Mapping[str, object] | None = None,
    ) -> ResultWrapper:
        statement, bound_params = _prepare_statement(sql, params)
        result = self._connection.execute(text(statement), bound_params)
        return ResultWrapper(result)

    def close(self) -> None:
        self._connection.close()


@contextmanager
def transactional_connection(engine: Engine) -> Iterator[SQLAlchemyConnectionWrapper]:
    # Always use an explicit transaction on a fresh connection so changes persist
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
