"""sqlite3-backed stand-in for backend/db.py so the SQL can be tested without MySQL.

install(db_module) swaps db.all/one/run/many/rowcount/transaction for sqlite versions and
translates the handful of MySQL-isms in schema.sql (AUTO_INCREMENT, ENGINE=, INDEX lines).
"""
import re
import sqlite3
from contextlib import asynccontextmanager
from pathlib import Path

SCHEMA = Path(__file__).resolve().parent.parent / "schema.sql"


def translate_schema(text: str) -> list:
    text = re.sub(r"--[^\n]*", "", text)
    text = re.sub(r"INT AUTO_INCREMENT PRIMARY KEY", "INTEGER PRIMARY KEY AUTOINCREMENT", text)
    text = re.sub(r"\)\s*ENGINE=InnoDB[^;]*;", ");", text)
    text = "\n".join(l for l in text.splitlines() if not re.match(r"\s*INDEX\s", l))
    return [s.strip() for s in text.split(";") if s.strip()]


class Conn:
    def __init__(self):
        self.c = sqlite3.connect(":memory:")
        self.c.row_factory = sqlite3.Row
        self.c.execute("PRAGMA foreign_keys = ON")
        for stmt in translate_schema(SCHEMA.read_text()):
            self.c.execute(stmt)

    @staticmethod
    def _sql(sql):
        return sql.replace("%s", "?")

    def all(self, sql, args=None):
        return [dict(r) for r in self.c.execute(self._sql(sql), tuple(args or ())).fetchall()]

    def one(self, sql, args=None):
        r = self.c.execute(self._sql(sql), tuple(args or ())).fetchone()
        return dict(r) if r else None

    def run(self, sql, args=None):
        cur = self.c.execute(self._sql(sql), tuple(args or ()))
        self.c.commit()
        return cur.lastrowid

    def rowcount(self, sql, args=None):
        cur = self.c.execute(self._sql(sql), tuple(args or ()))
        self.c.commit()
        return cur.rowcount

    def many(self, sql, seq):
        self.c.executemany(self._sql(sql), list(seq))
        self.c.commit()


def install(db_module) -> Conn:
    conn = Conn()

    async def _all(sql, args=None): return conn.all(sql, args)
    async def _one(sql, args=None): return conn.one(sql, args)
    async def _run(sql, args=None): return conn.run(sql, args)
    async def _rowcount(sql, args=None): return conn.rowcount(sql, args)
    async def _many(sql, seq): return conn.many(sql, seq)

    class _Tx:
        all = staticmethod(_all); one = staticmethod(_one); run = staticmethod(_run)
        rowcount = staticmethod(_rowcount); many = staticmethod(_many)

    @asynccontextmanager
    async def _transaction():
        yield _Tx()

    db_module.all, db_module.one, db_module.run = _all, _one, _run
    db_module.rowcount, db_module.many, db_module.transaction = _rowcount, _many, _transaction
    return conn
