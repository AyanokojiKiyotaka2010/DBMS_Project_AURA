"""Thin async MySQL layer (aiomysql).

Usage:
    rows = await db.all("SELECT * FROM users WHERE role=%s", ("Student",))
    row  = await db.one("SELECT * FROM users WHERE id=%s", (5,))
    new_id = await db.run("INSERT INTO departments (name) VALUES (%s)", ("CSE",))

    async with db.transaction() as tx:          # several statements, one commit
        await tx.run(...); await tx.all(...)

The same four verbs (all / one / run / many + transaction) are what the unit tests
re-implement on top of sqlite3, so keep application SQL to the portable subset
(no INSERT IGNORE, no GROUP_CONCAT, no ON DUPLICATE KEY) wherever practical.
"""
import os
import re
from contextlib import asynccontextmanager
from pathlib import Path

try:  # optional at import time so the SQL layer can be unit-tested on sqlite
    import aiomysql
except ImportError:  # pragma: no cover
    aiomysql = None

_pool = None
SCHEMA_PATH = Path(__file__).parent / "schema.sql"


async def init_pool():
    global _pool
    if _pool is not None:
        return _pool
    _pool = await aiomysql.create_pool(
        host=os.environ.get("MYSQL_HOST", "127.0.0.1"),
        port=int(os.environ.get("MYSQL_PORT", "3306")),
        user=os.environ.get("MYSQL_USER", "root"),
        password=os.environ.get("MYSQL_PASSWORD", ""),
        db=os.environ.get("MYSQL_DATABASE", "aura"),
        charset="utf8mb4",
        autocommit=True,
        minsize=1,
        maxsize=int(os.environ.get("MYSQL_POOL_SIZE", "10")),
        init_command="SET time_zone='+00:00'",
    )
    return _pool


async def close_pool():
    global _pool
    if _pool is not None:
        _pool.close()
        await _pool.wait_closed()
        _pool = None


class _Tx:
    """Statement runner bound to a single cursor (used inside transaction())."""

    def __init__(self, cur):
        self._cur = cur

    async def all(self, sql, args=None):
        await self._cur.execute(sql, args or ())
        return list(await self._cur.fetchall())

    async def one(self, sql, args=None):
        await self._cur.execute(sql, args or ())
        return await self._cur.fetchone()

    async def run(self, sql, args=None):
        """Execute a write; returns lastrowid (0 when the table has no AUTO_INCREMENT)."""
        await self._cur.execute(sql, args or ())
        return self._cur.lastrowid

    async def rowcount(self, sql, args=None):
        await self._cur.execute(sql, args or ())
        return self._cur.rowcount

    async def many(self, sql, seq):
        if seq:
            await self._cur.executemany(sql, seq)


@asynccontextmanager
async def transaction():
    async with _pool.acquire() as conn:
        await conn.begin()
        try:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                yield _Tx(cur)
            await conn.commit()
        except BaseException:
            await conn.rollback()
            raise


async def all(sql, args=None):  # noqa: A001 - intentional verb name
    async with _pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            return await _Tx(cur).all(sql, args)


async def one(sql, args=None):
    async with _pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            return await _Tx(cur).one(sql, args)


async def run(sql, args=None):
    async with _pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            return await _Tx(cur).run(sql, args)


async def rowcount(sql, args=None):
    async with _pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            return await _Tx(cur).rowcount(sql, args)


async def many(sql, seq):
    async with _pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await _Tx(cur).many(sql, seq)


def split_sql(text: str):
    """Split a .sql script into statements (strips -- comments; no ';' inside literals allowed)."""
    text = re.sub(r"--[^\n]*", "", text)
    return [s.strip() for s in text.split(";") if s.strip()]


async def ensure_schema():
    """Create every table that does not exist yet (CREATE TABLE IF NOT EXISTS is idempotent)."""
    for stmt in split_sql(SCHEMA_PATH.read_text(encoding="utf-8")):
        await run(stmt)
