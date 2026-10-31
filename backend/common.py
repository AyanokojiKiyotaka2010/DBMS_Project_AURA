"""Shared helpers: auth, time conversion, user serialisation, attachment validation."""
import os
from datetime import datetime, timedelta, timezone
from typing import List

import bcrypt
import jwt
from fastapi import HTTPException, Request

import db

JWT_SECRET = os.environ.get("JWT_SECRET", "aura_campus_secret_change_me")
JWT_ALG = "HS256"

ALLOWED_ROLES = {"Student", "CR", "DCR", "Senior", "Alumni", "Professor", "Convener", "Administrator"}
SELF_REGISTER_ROLES = {"Student", "Senior", "Alumni"}      # take effect immediately
REQUESTABLE_ROLES = {"Professor", "CR", "DCR", "Convener"}   # sign-up creates a Student + a pending request an Administrator approves
STUDENT_ROLES = ("Student", "CR", "DCR")


# ---------------------------------------------------------------- passwords / tokens
def hash_pw(pw: str) -> str:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()


def verify_pw(pw: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(pw.encode(), hashed.encode())
    except Exception:
        return False


def make_token(user_id, email: str, kind: str = "access") -> str:
    exp = datetime.now(timezone.utc) + (timedelta(hours=24) if kind == "access" else timedelta(days=7))
    return jwt.encode({"sub": str(user_id), "email": email, "type": kind, "exp": exp}, JWT_SECRET, algorithm=JWT_ALG)


def set_auth_cookies(response, uid, email: str):
    access = make_token(uid, email, "access")
    refresh = make_token(uid, email, "refresh")
    for name, val, age in [("access_token", access, 86400), ("refresh_token", refresh, 604800)]:
        response.set_cookie(key=name, value=val, httponly=True, secure=True, samesite="none", max_age=age, path="/")
    return access


# ---------------------------------------------------------------- time
def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def to_db(dt: datetime) -> datetime:
    """aware/naive datetime -> naive UTC (what DATETIME columns hold)."""
    if dt is None:
        return None
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc)
    return dt.replace(tzinfo=None, microsecond=0)


def from_db(v):
    """DATETIME value (datetime, or 'YYYY-MM-DD HH:MM:SS' string) -> aware UTC datetime."""
    if v is None:
        return None
    if isinstance(v, str):
        v = datetime.fromisoformat(v.replace("Z", "+00:00"))
    return v if v.tzinfo else v.replace(tzinfo=timezone.utc)


def iso(v) -> str:
    """Anything datetime-ish -> ISO-8601 string with explicit UTC offset (or None)."""
    d = from_db(v)
    return d.isoformat() if d else None


def parse_iso(s):
    """Client string -> aware UTC datetime. Naive input is treated as UTC. Bad input -> None."""
    if not s:
        return None
    try:
        return from_db(datetime.fromisoformat(str(s).replace("Z", "+00:00")))
    except Exception:
        return None


# ---------------------------------------------------------------- users
USER_SQL = (
    "SELECT u.id, u.name, u.email, u.password_hash, u.role, u.requested_role, u.department_id, u.year_id, u.division_id, "
    "       u.roll_no, u.avatar, u.created_at, "
    "       d.name AS department_name, y.label AS year_label, dv.name AS division_name "
    "FROM users u "
    "LEFT JOIN departments d ON d.id = u.department_id "
    "LEFT JOIN academic_years y ON y.id = u.year_id "
    "LEFT JOIN divisions dv ON dv.id = u.division_id "
)


async def fetch_user(where: str, args: tuple):
    return await db.one(USER_SQL + "WHERE " + where, args)


def user_public(u: dict) -> dict:
    role = u.get("role", "Student")
    return {
        "user_id": str(u["id"]),
        "name": u.get("name"),
        "email": u.get("email"),
        "role": role,
        "requested_role": u.get("requested_role") or "",
        "department": u.get("department_name") or ("Administration" if role == "Administrator" else ""),
        "year": u.get("year_label") or "",
        "division": u.get("division_name") or "",
        "department_id": u.get("department_id"),
        "year_id": u.get("year_id"),
        "division_id": u.get("division_id"),
        "roll_no": u.get("roll_no") or "",
        "avatar": u.get("avatar") or "",
    }


async def user_from_token(token: str):
    """Decode an access token and load the user row (None when invalid)."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
        if payload.get("type") != "access":
            return None
        return await fetch_user("u.id = %s", (int(payload["sub"]),))
    except Exception:
        return None


async def get_user(request: Request) -> dict:
    token = request.cookies.get("access_token")
    if not token:
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            token = auth[7:]
    if not token:
        raise HTTPException(401, "Not authenticated")
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Invalid token")
    if payload.get("type") != "access":
        raise HTTPException(401, "Invalid token type")
    row = await fetch_user("u.id = %s", (int(payload["sub"]),))
    if not row:
        raise HTTPException(401, "User not found")
    return user_public(row)


def require_role(user: dict, allowed: list):
    if user["role"] not in allowed:
        raise HTTPException(403, f"Requires role in {allowed}")


# ---------------------------------------------------------------- lookups
async def dept_id_by_name(name):
    if not name:
        return None
    r = await db.one("SELECT id FROM departments WHERE name=%s", (name,))
    return r["id"] if r else None


async def year_id_by_label(label):
    if not label:
        return None
    r = await db.one("SELECT id FROM academic_years WHERE label=%s", (label,))
    return r["id"] if r else None


# ---------------------------------------------------------------- attachments
MAX_ATTACHMENT_BYTES = 2 * 1024 * 1024   # 2 MB per file (base64 decoded)
MAX_ATTACHMENTS_PER_ITEM = 3


def validate_attachments(items: List[dict]) -> List[dict]:
    """Validate and normalise a list of {name, mime, data (base64 string)} attachments."""
    if not items:
        return []
    if len(items) > MAX_ATTACHMENTS_PER_ITEM:
        raise HTTPException(400, f"Max {MAX_ATTACHMENTS_PER_ITEM} attachments per item")
    cleaned = []
    for a in items:
        name = (a.get("name") or "file").strip()[:80]
        mime = (a.get("mime") or "application/octet-stream").strip()[:100]
        data = a.get("data") or ""
        if not isinstance(data, str) or not data:
            continue
        approx_bytes = int(len(data) * 0.75)
        if approx_bytes > MAX_ATTACHMENT_BYTES:
            raise HTTPException(400, f"'{name}' exceeds 2MB limit")
        cleaned.append({"name": name, "mime": mime, "data": data, "size": approx_bytes})
    return cleaned


_ATT_TABLES = {"query": ("query_attachments", "query_id"), "complaint": ("complaint_attachments", "complaint_id")}


async def save_attachments(tx, kind: str, owner_id: int, items: List[dict]):
    table, col = _ATT_TABLES[kind]
    await tx.many(
        f"INSERT INTO {table} ({col}, name, mime, size, data) VALUES (%s,%s,%s,%s,%s)",
        [(owner_id, a["name"], a["mime"], a["size"], a["data"]) for a in items],
    )


async def load_attachments(kind: str, owner_ids: list) -> dict:
    """{owner_id: [ {name,mime,data,size}, ... ]}"""
    if not owner_ids:
        return {}
    table, col = _ATT_TABLES[kind]
    marks = ",".join(["%s"] * len(owner_ids))
    rows = await db.all(f"SELECT {col} AS owner, name, mime, size, data FROM {table} WHERE {col} IN ({marks}) ORDER BY id",
                        tuple(owner_ids))
    out = {}
    for r in rows:
        out.setdefault(r["owner"], []).append({"name": r["name"], "mime": r["mime"], "data": r["data"], "size": r["size"]})
    return out
