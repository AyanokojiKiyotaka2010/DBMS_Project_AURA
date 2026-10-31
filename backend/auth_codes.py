"""One-time e-mail codes (verify address / reset password). Only a salted hash of the code is stored."""
import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta

import db
from common_time import now_db

CODE_TTL = timedelta(minutes=15)
MAX_ATTEMPTS = 5
RESEND_SECONDS = 60


class CodeError(Exception):
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.message, self.status = message, status


def _hash(code: str, uid: int, purpose: str) -> str:
    secret = os.environ.get("JWT_SECRET", "aura_campus_secret_change_me")
    return hashlib.sha256(f"{purpose}:{uid}:{code}:{secret}".encode()).hexdigest()


def _dt(v):
    return datetime.fromisoformat(v) if isinstance(v, str) else v


async def issue_code(uid: int, purpose: str) -> str:
    now = now_db()
    last = await db.one("SELECT created_at FROM email_codes WHERE user_id=%s AND purpose=%s ORDER BY id DESC LIMIT 1", (uid, purpose))
    if last:
        wait = RESEND_SECONDS - (now - _dt(last["created_at"])).total_seconds()
        if wait > 0:
            raise CodeError(f"Please wait {int(wait) + 1} seconds before asking for another code.", 429)
    code = f"{secrets.randbelow(1_000_000):06d}"
    await db.run("DELETE FROM email_codes WHERE user_id=%s AND purpose=%s", (uid, purpose))
    await db.run("INSERT INTO email_codes (user_id,purpose,code_hash,expires_at,attempts,created_at) VALUES (%s,%s,%s,%s,0,%s)",
                 (uid, purpose, _hash(code, uid, purpose), now + CODE_TTL, now))
    return code


async def check_code(uid: int, purpose: str, code: str) -> bool:
    """True once, for the right unexpired code; wrong guesses are counted and the code dies after MAX_ATTEMPTS."""
    row = await db.one("SELECT id, code_hash, expires_at, attempts FROM email_codes WHERE user_id=%s AND purpose=%s "
                       "ORDER BY id DESC LIMIT 1", (uid, purpose))
    if not row or row["attempts"] >= MAX_ATTEMPTS or _dt(row["expires_at"]) < now_db():
        return False
    if not hmac.compare_digest(_hash((code or "").strip(), uid, purpose), row["code_hash"]):
        await db.run("UPDATE email_codes SET attempts = attempts + 1 WHERE id=%s", (row["id"],))
        return False
    await db.run("DELETE FROM email_codes WHERE user_id=%s AND purpose=%s", (uid, purpose))
    return True
