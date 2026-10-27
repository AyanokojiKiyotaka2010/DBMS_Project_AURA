"""AURA — Campus Academic & Club Community Platform Backend (MySQL edition).

Key modules:
- JWT auth (HTTP-only cookies + bearer fallback)
- Announcements (CR/DCR gated posting per department/year)
- Personal attendance tracker (per-user subjects)
- Anonymous queries with escalation (48h -> seniors, 7d -> alumni, 7d after resolve -> archive)
- Clubs + 5-year archives (created by Administrator / Convener / Professor — nothing is seeded)
- Temporary groups with auto-expiry
- Complaints
- Admin role management
- Academic structure, courses, marks, class attendance  (academics.py)
- Role-scoped reports                                   (reports.py)
"""
import asyncio
import json
import logging
import os
import uuid
from contextlib import asynccontextmanager
from datetime import timedelta
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Response, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, EmailStr
from starlette.middleware.cors import CORSMiddleware

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

import db  # noqa: E402  (after load_dotenv so env vars are visible)
from common import (  # noqa: E402
    ALLOWED_ROLES, SELF_REGISTER_ROLES, USER_SQL, dept_id_by_name, fetch_user, from_db, get_user, hash_pw, iso,
    load_attachments, now_utc, parse_iso, require_role, save_attachments, set_auth_cookies, to_db,
    user_from_token, user_public, validate_attachments, verify_pw, year_id_by_label,
)
import academics  # noqa: E402
import reports  # noqa: E402

ESCALATE_TO_SENIOR_HOURS = 48
ESCALATE_TO_ALUMNI_DAYS = 7
ARCHIVE_AFTER_RESOLVE_DAYS = 7
logger = logging.getLogger("aura")
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")


# ---------------------------------------------------------------- lifecycle
async def bootstrap_admin():
    """First-run convenience: if the system has no Administrator, create one from env vars."""
    if await db.one("SELECT id FROM users WHERE role='Administrator' LIMIT 1"):
        return
    email = os.environ.get("ADMIN_EMAIL", "admin@campus.edu").lower().strip()
    pw = os.environ.get("ADMIN_PASSWORD", "admin123")
    name = os.environ.get("ADMIN_NAME", "Campus Admin")
    await db.run(
        "INSERT INTO users (name,email,password_hash,role,created_at) VALUES (%s,%s,%s,'Administrator',%s)",
        (name, email, hash_pw(pw), to_db(now_utc())),
    )
    logger.warning("Created bootstrap administrator %s — change this password after first login.", email)


@asynccontextmanager
async def lifespan(_: FastAPI):
    await db.init_pool()
    await db.ensure_schema()
    await bootstrap_admin()
    yield
    await db.close_pool()


app = FastAPI(title="AURA Campus API", version="3.0", lifespan=lifespan)
api = APIRouter(prefix="/api")


# ---------------------------------------------------------------- helpers
def compute_stage(status: str, created_at) -> str:
    if status == "Archived":
        return "archived"
    if status == "Resolved":
        return "resolved"
    created = from_db(created_at) or now_utc()
    age = now_utc() - created
    if age >= timedelta(days=ESCALATE_TO_ALUMNI_DAYS):
        return "alumni"
    if age >= timedelta(hours=ESCALATE_TO_SENIOR_HOURS):
        return "seniors"
    return "peers"


def _in(n: int) -> str:
    return ",".join(["%s"] * n)


# ---------------------------------------------------------------- schemas
class UserRegister(BaseModel):
    name: str
    email: EmailStr
    password: str
    department_id: Optional[int] = None
    year_id: Optional[int] = None
    division_id: Optional[int] = None
    roll_no: Optional[str] = None
    role: Optional[str] = "Student"


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class AnnouncementCreate(BaseModel):
    title: str
    body: str
    kind: Optional[str] = "general"
    deadline: Optional[str] = None
    department: Optional[str] = ""
    year: Optional[str] = ""


class AttendanceCreate(BaseModel):
    code: str
    name: str


class AttendanceMark(BaseModel):
    present: bool = True


class QueryCreate(BaseModel):
    department: str
    topic: Optional[str] = "General"
    query: str
    attachments: Optional[List[dict]] = []


class AnswerCreate(BaseModel):
    text: str


class TempGroupCreate(BaseModel):
    name: str
    hours: int = 24


class ComplaintCreate(BaseModel):
    subject: str
    body: str
    attachments: Optional[List[dict]] = []


class ComplaintRespond(BaseModel):
    response: str


class RoleUpdate(BaseModel):
    role: str


class ArchiveYear(BaseModel):
    year: int
    events: int = 0


class ClubCreate(BaseModel):
    name: str
    category: Optional[str] = ""
    description: Optional[str] = ""
    cover: Optional[str] = ""
    cells: Optional[List[str]] = []
    archives: Optional[List[ArchiveYear]] = []


class ClubUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    cover: Optional[str] = None


class CellCreate(BaseModel):
    name: str


# ---------------------------------------------------------------- websocket manager
class ConnectionManager:
    """Tracks live WS connections and broadcasts campus-wide events."""

    def __init__(self):
        self.active: set = set()
        self.meta: dict = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, user: dict):
        await websocket.accept()
        async with self._lock:
            self.active.add(websocket)
            self.meta[websocket] = {"user_id": user.get("user_id"), "department": user.get("department"),
                                    "year": user.get("year")}

    async def disconnect(self, websocket: WebSocket):
        async with self._lock:
            self.active.discard(websocket)
            self.meta.pop(websocket, None)

    async def broadcast(self, message: dict, *, department: str = None):
        text = json.dumps(message, default=str)
        dead = []
        async with self._lock:
            snapshot = list(self.active)
        for ws in snapshot:
            meta = self.meta.get(ws) or {}
            if department and meta.get("department") not in (department, "Administration"):
                continue
            try:
                await ws.send_text(text)
            except Exception:
                dead.append(ws)
        for ws in dead:
            await self.disconnect(ws)

    def stats(self):
        return {"connections": len(self.active)}


manager = ConnectionManager()


# ================================================================= Auth
@api.get("/meta/structure")
async def meta_structure():
    """Public: departments / years / divisions for the sign-up form (admin-managed)."""
    return await academics.structure()


@api.post("/auth/register")
async def register(inp: UserRegister, response: Response):
    email = inp.email.lower().strip()
    role = inp.role or "Student"
    if role not in SELF_REGISTER_ROLES:
        raise HTTPException(400, "Self-registration is limited to Student, Senior and Alumni. "
                                 "Professor / CR / DCR roles are granted by an Administrator.")
    if await db.one("SELECT id FROM users WHERE email=%s", (email,)):
        raise HTTPException(400, "Email already registered")

    # validate the academic placement against what the admin has configured
    if inp.department_id is not None and not await db.one("SELECT id FROM departments WHERE id=%s", (inp.department_id,)):
        raise HTTPException(400, "Unknown department")
    if inp.year_id is not None and not await db.one("SELECT id FROM academic_years WHERE id=%s", (inp.year_id,)):
        raise HTTPException(400, "Unknown year")
    if inp.division_id is not None:
        dv = await db.one("SELECT department_id, year_id FROM divisions WHERE id=%s", (inp.division_id,))
        if not dv:
            raise HTTPException(400, "Unknown division")
        if dv["department_id"] != inp.department_id or dv["year_id"] != inp.year_id:
            raise HTTPException(400, "Division does not belong to the chosen department / year")
    roll = (inp.roll_no or "").strip() or None
    if roll and await db.one("SELECT id FROM users WHERE roll_no=%s", (roll,)):
        raise HTTPException(400, "Roll number already registered")

    uid = await db.run(
        "INSERT INTO users (name,email,password_hash,role,department_id,year_id,division_id,roll_no,created_at) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        (inp.name.strip(), email, hash_pw(inp.password), role, inp.department_id, inp.year_id,
         inp.division_id, roll, to_db(now_utc())),
    )
    set_auth_cookies(response, uid, email)
    return {"user": user_public(await fetch_user("u.id=%s", (uid,)))}


@api.post("/auth/login")
async def login(inp: UserLogin, response: Response):
    email = inp.email.lower().strip()
    u = await fetch_user("u.email=%s", (email,))
    if not u or not verify_pw(inp.password, u["password_hash"]):
        raise HTTPException(401, "Invalid email or password")
    set_auth_cookies(response, u["id"], email)
    return {"user": user_public(u)}


@api.post("/auth/logout")
async def logout(response: Response):
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")
    return {"ok": True}


@api.get("/auth/me")
async def me(user=Depends(get_user)):
    return user


# ================================================================= Announcements
def _ann_out(r: dict) -> dict:
    return {
        "id": str(r["id"]), "title": r["title"], "body": r["body"], "kind": r["kind"],
        "deadline": iso(r.get("deadline")), "department": r.get("department") or "", "year": r.get("year") or "",
        "author": r["author_name"], "author_id": str(r["author_id"]) if r.get("author_id") is not None else None,
        "author_role": r["author_role"], "created_at": iso(r["created_at"]),
    }


_ANN_SELECT = (
    "SELECT a.id, a.title, a.body, a.kind, a.deadline, a.author_id, a.author_name, a.author_role, a.created_at, "
    "       d.name AS department, y.label AS year "
    "FROM announcements a "
    "LEFT JOIN departments d ON d.id = a.department_id "
    "LEFT JOIN academic_years y ON y.id = a.year_id "
)


@api.get("/announcements")
async def list_announcements(department: str = "", year: str = "", user=Depends(get_user)):
    # Year is deliberately not filtered: cross-year notices stay visible (same as before).
    if department:
        rows = await db.all(_ANN_SELECT + "WHERE d.name=%s ORDER BY a.created_at DESC LIMIT 200", (department,))
    else:
        rows = await db.all(_ANN_SELECT + "ORDER BY a.created_at DESC LIMIT 200")
    return [_ann_out(r) for r in rows]


@api.post("/announcements")
async def create_announcement(inp: AnnouncementCreate, user=Depends(get_user)):
    require_role(user, ["CR", "DCR", "Administrator", "Professor"])
    dept_id = await dept_id_by_name(inp.department) if inp.department else user["department_id"]
    year_id = await year_id_by_label(inp.year) if inp.year else user["year_id"]
    deadline = parse_iso(inp.deadline)
    aid = await db.run(
        "INSERT INTO announcements (title,body,kind,deadline,department_id,year_id,author_id,author_name,author_role,created_at) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        (inp.title.strip(), inp.body.strip(), inp.kind or "general", to_db(deadline), dept_id, year_id,
         int(user["user_id"]), user["name"], user["role"], to_db(now_utc())),
    )
    doc = _ann_out(await db.one(_ANN_SELECT + "WHERE a.id=%s", (aid,)))
    await manager.broadcast({"type": "announcement.created", "payload": doc}, department=doc.get("department") or None)
    return doc


# ================================================================= Personal attendance tracker
def _sub_out(r: dict) -> dict:
    return {"id": str(r["id"]), "user_id": str(r["user_id"]), "code": r["code"], "name": r["name"],
            "attended": r["attended"], "total": r["total"]}


@api.get("/attendance")
async def list_attendance(user=Depends(get_user)):
    rows = await db.all("SELECT * FROM self_attendance WHERE user_id=%s ORDER BY id LIMIT 100", (int(user["user_id"]),))
    return [_sub_out(r) for r in rows]


@api.post("/attendance")
async def add_attendance(inp: AttendanceCreate, user=Depends(get_user)):
    sid = await db.run("INSERT INTO self_attendance (user_id, code, name, attended, total) VALUES (%s,%s,%s,0,0)",
                       (int(user["user_id"]), inp.code.upper().strip(), inp.name.strip()))
    return _sub_out(await db.one("SELECT * FROM self_attendance WHERE id=%s", (sid,)))


@api.post("/attendance/{sub_id}/mark")
async def mark_attendance(sub_id: int, inp: AttendanceMark, user=Depends(get_user)):
    n = await db.rowcount(
        "UPDATE self_attendance SET total = total + 1, attended = attended + %s WHERE id=%s AND user_id=%s",
        (1 if inp.present else 0, sub_id, int(user["user_id"])),
    )
    if not n:
        raise HTTPException(404, "Subject not found")
    return {"ok": True}


# ================================================================= Queries (anonymous)
_Q_SELECT = (
    "SELECT q.id, q.topic, q.query_text, q.author_encrypted_id, q.real_author_id, q.status, q.created_at, "
    "       q.resolved_at, d.name AS department "
    "FROM queries q LEFT JOIN departments d ON d.id = q.department_id "
)


async def _queries_out(rows: list, viewer_id: str) -> list:
    ids = [r["id"] for r in rows]
    answers, atts = {}, await load_attachments("query", ids)
    if ids:
        for a in await db.all(
            f"SELECT query_id, user_id, author_name, role, text, created_at FROM query_answers "
            f"WHERE query_id IN ({_in(len(ids))}) ORDER BY id", tuple(ids)):
            answers.setdefault(a["query_id"], []).append({
                "author": a["author_name"], "role": a["role"],
                "user_id": str(a["user_id"]) if a["user_id"] is not None else None,
                "text": a["text"], "time": iso(a["created_at"]),
            })
    out = []
    for r in rows:
        mine = r["real_author_id"] is not None and str(r["real_author_id"]) == viewer_id
        out.append({
            "id": str(r["id"]), "department": r.get("department") or "", "topic": r["topic"], "query": r["query_text"],
            "author_encrypted_id": r["author_encrypted_id"],
            # anonymity: the real author id is only ever revealed to the author themself
            "real_author_id": str(r["real_author_id"]) if mine else None,
            "status": r["status"], "answers": answers.get(r["id"], []), "attachments": atts.get(r["id"], []),
            "created_at": iso(r["created_at"]), "resolved_at": iso(r.get("resolved_at")),
            "stage": compute_stage(r["status"], r["created_at"]),
        })
    return out


@api.get("/queries")
async def list_queries(archived: bool = False, user=Depends(get_user)):
    # auto-archive resolved queries older than N days
    cutoff = to_db(now_utc() - timedelta(days=ARCHIVE_AFTER_RESOLVE_DAYS))
    await db.run("UPDATE queries SET status='Archived' WHERE status='Resolved' AND resolved_at <= %s", (cutoff,))
    cond = "q.status = 'Archived'" if archived else "q.status <> 'Archived'"
    rows = await db.all(_Q_SELECT + f"WHERE {cond} ORDER BY q.created_at DESC LIMIT 200")
    return await _queries_out(rows, user["user_id"])


@api.post("/queries")
async def create_query(inp: QueryCreate, user=Depends(get_user)):
    attachments = validate_attachments(inp.attachments or [])
    dept_id = await dept_id_by_name(inp.department)   # unknown / free-text department -> campus-wide query
    async with db.transaction() as tx:
        qid = await tx.run(
            "INSERT INTO queries (department_id,topic,query_text,author_encrypted_id,real_author_id,status,created_at) "
            "VALUES (%s,%s,%s,%s,%s,'Open',%s)",
            (dept_id, inp.topic or "General", inp.query.strip(), f"enc_usr_{uuid.uuid4().hex[:10]}",
             int(user["user_id"]), to_db(now_utc())),
        )
        await save_attachments(tx, "query", qid, attachments)
    doc = (await _queries_out(await db.all(_Q_SELECT + "WHERE q.id=%s", (qid,)), user["user_id"]))[0]
    broadcast_doc = {**doc, "real_author_id": None}      # never push the author's identity to other clients
    await manager.broadcast({"type": "query.created", "payload": broadcast_doc}, department=doc.get("department") or None)
    return doc


@api.post("/queries/{qid}/answer")
async def answer_query(qid: int, inp: AnswerCreate, user=Depends(get_user)):
    q = await db.one(_Q_SELECT + "WHERE q.id=%s", (qid,))
    if not q:
        raise HTTPException(404, "Query not found")
    now = now_utc()
    async with db.transaction() as tx:
        await tx.run(
            "INSERT INTO query_answers (query_id,user_id,author_name,role,text,created_at) VALUES (%s,%s,%s,%s,%s,%s)",
            (qid, int(user["user_id"]), user["name"], user["role"], inp.text.strip(), to_db(now)),
        )
        await tx.run("UPDATE queries SET status='Answered' WHERE id=%s", (qid,))
    ans = {"author": user["name"], "role": user["role"], "user_id": user["user_id"],
           "text": inp.text.strip(), "time": iso(now)}
    await manager.broadcast(
        {"type": "query.answered", "payload": {"query_id": str(qid), "answer": ans, "department": q.get("department")}},
        department=q.get("department") or None,
    )
    return {"ok": True, "answer": ans}


@api.post("/queries/{qid}/resolve")
async def resolve_query(qid: int, user=Depends(get_user)):
    q = await db.one("SELECT id, real_author_id FROM queries WHERE id=%s", (qid,))
    if not q:
        raise HTTPException(404, "Query not found")
    if str(q["real_author_id"]) != user["user_id"] and user["role"] not in ("Administrator", "Professor"):
        raise HTTPException(403, "Only the author, professor or admin can resolve")
    await db.run("UPDATE queries SET status='Resolved', resolved_at=%s WHERE id=%s", (to_db(now_utc()), qid))
    return {"ok": True}


# ================================================================= Clubs (manually created)
CLUB_MANAGERS = ["Administrator", "Convener", "Professor"]


async def _clubs_out(where: str = "", args: tuple = ()) -> list:
    clubs = await db.all("SELECT id, name, category, description, cover, created_at FROM clubs "
                         + where + " ORDER BY name", args)
    if not clubs:
        return []
    ids = tuple(c["id"] for c in clubs)
    cells, arch = {}, {}
    for r in await db.all(f"SELECT id, club_id, name FROM club_cells WHERE club_id IN ({_in(len(ids))}) ORDER BY id", ids):
        cells.setdefault(r["club_id"], []).append(r["name"])
    for r in await db.all(f"SELECT club_id, year, events FROM club_archives WHERE club_id IN ({_in(len(ids))}) ORDER BY year", ids):
        arch.setdefault(r["club_id"], []).append({"year": r["year"], "events": r["events"]})
    return [{"id": c["id"], "name": c["name"], "category": c["category"], "description": c["description"],
             "cover": c["cover"], "cells": cells.get(c["id"], []), "archives": arch.get(c["id"], [])} for c in clubs]


@api.get("/clubs")
async def list_clubs(user=Depends(get_user)):
    return await _clubs_out()


@api.post("/clubs")
async def create_club(inp: ClubCreate, user=Depends(get_user)):
    require_role(user, CLUB_MANAGERS)
    name = inp.name.strip()
    if not name:
        raise HTTPException(400, "Club name is required")
    if await db.one("SELECT id FROM clubs WHERE name=%s", (name,)):
        raise HTTPException(400, "A club with that name already exists")
    async with db.transaction() as tx:
        cid = await tx.run(
            "INSERT INTO clubs (name,category,description,cover,created_by,created_at) VALUES (%s,%s,%s,%s,%s,%s)",
            (name, (inp.category or "").strip(), (inp.description or "").strip(), (inp.cover or "").strip(),
             int(user["user_id"]), to_db(now_utc())),
        )
        cells = sorted({c.strip() for c in (inp.cells or []) if c and c.strip()})
        await tx.many("INSERT INTO club_cells (club_id,name) VALUES (%s,%s)", [(cid, c) for c in cells])
        years = {a.year: a.events for a in (inp.archives or [])}
        await tx.many("INSERT INTO club_archives (club_id,year,events) VALUES (%s,%s,%s)",
                      [(cid, y, e) for y, e in years.items()])
    return (await _clubs_out("WHERE id=%s", (cid,)))[0]


@api.put("/clubs/{club_id}")
async def update_club(club_id: int, inp: ClubUpdate, user=Depends(get_user)):
    require_role(user, CLUB_MANAGERS)
    fields = {k: (v.strip() if isinstance(v, str) else v) for k, v in inp.model_dump().items() if v is not None}
    if "name" in fields and not fields["name"]:
        raise HTTPException(400, "Club name cannot be empty")
    if fields:
        sets = ", ".join(f"{k}=%s" for k in fields)       # keys come from the pydantic model, not the client
        try:
            await db.rowcount(f"UPDATE clubs SET {sets} WHERE id=%s", tuple(fields.values()) + (club_id,))
        except Exception:
            raise HTTPException(400, "Could not update (is the name already used?)")
    club = await _clubs_out("WHERE id=%s", (club_id,))
    if not club:
        raise HTTPException(404, "Club not found")
    return club[0]


@api.delete("/clubs/{club_id}")
async def delete_club(club_id: int, user=Depends(get_user)):
    require_role(user, CLUB_MANAGERS)
    if not await db.rowcount("DELETE FROM clubs WHERE id=%s", (club_id,)):
        raise HTTPException(404, "Club not found")
    return {"ok": True}


@api.post("/clubs/{club_id}/cells")
async def add_cell(club_id: int, inp: CellCreate, user=Depends(get_user)):
    require_role(user, CLUB_MANAGERS)
    name = inp.name.strip()
    if not name:
        raise HTTPException(400, "Cell name is required")
    if not await db.one("SELECT id FROM clubs WHERE id=%s", (club_id,)):
        raise HTTPException(404, "Club not found")
    if not await db.one("SELECT id FROM club_cells WHERE club_id=%s AND name=%s", (club_id, name)):
        await db.run("INSERT INTO club_cells (club_id,name) VALUES (%s,%s)", (club_id, name))
    return (await _clubs_out("WHERE id=%s", (club_id,)))[0]


@api.delete("/clubs/{club_id}/cells/{name}")
async def remove_cell(club_id: int, name: str, user=Depends(get_user)):
    require_role(user, CLUB_MANAGERS)
    await db.run("DELETE FROM club_cells WHERE club_id=%s AND name=%s", (club_id, name))
    return {"ok": True}


@api.post("/clubs/{club_id}/archives")
async def set_archive(club_id: int, inp: ArchiveYear, user=Depends(get_user)):
    """Add or overwrite one year's event count in a club's archive."""
    require_role(user, CLUB_MANAGERS)
    if inp.year < 1900 or inp.year > 2200 or inp.events < 0:
        raise HTTPException(400, "Invalid year or event count")
    if not await db.one("SELECT id FROM clubs WHERE id=%s", (club_id,)):
        raise HTTPException(404, "Club not found")
    async with db.transaction() as tx:
        await tx.run("DELETE FROM club_archives WHERE club_id=%s AND year=%s", (club_id, inp.year))
        await tx.run("INSERT INTO club_archives (club_id,year,events) VALUES (%s,%s,%s)", (club_id, inp.year, inp.events))
    return (await _clubs_out("WHERE id=%s", (club_id,)))[0]


# ================================================================= Temporary groups
async def _temp_out(where: str = "", args: tuple = ()) -> list:
    groups = await db.all("SELECT id, name, creator_id, creator_name, created_at, expires_at FROM temp_groups "
                          + where + " ORDER BY expires_at", args)
    members = {}
    if groups:
        ids = tuple(g["id"] for g in groups)
        for m in await db.all(f"SELECT group_id, user_id FROM temp_group_members WHERE group_id IN ({_in(len(ids))})", ids):
            members.setdefault(m["group_id"], []).append(str(m["user_id"]))
    return [{"id": str(g["id"]), "name": g["name"],
             "creator_id": str(g["creator_id"]) if g["creator_id"] is not None else None,
             "creator_name": g["creator_name"], "members": members.get(g["id"], []),
             "created_at": iso(g["created_at"]), "expires_at": iso(g["expires_at"])} for g in groups]


@api.get("/temp-groups")
async def list_temp(user=Depends(get_user)):
    # auto-expire: members go with the group (ON DELETE CASCADE)
    await db.run("DELETE FROM temp_groups WHERE expires_at < %s", (to_db(now_utc()),))
    return await _temp_out()


@api.post("/temp-groups")
async def create_temp(inp: TempGroupCreate, user=Depends(get_user)):
    if inp.hours < 1 or inp.hours > 24 * 30:
        raise HTTPException(400, "hours must be between 1 and 720")
    now = now_utc()
    async with db.transaction() as tx:
        gid = await tx.run(
            "INSERT INTO temp_groups (name,creator_id,creator_name,created_at,expires_at) VALUES (%s,%s,%s,%s,%s)",
            (inp.name.strip(), int(user["user_id"]), user["name"], to_db(now), to_db(now + timedelta(hours=inp.hours))),
        )
        await tx.run("INSERT INTO temp_group_members (group_id,user_id) VALUES (%s,%s)", (gid, int(user["user_id"])))
    return (await _temp_out("WHERE id=%s", (gid,)))[0]


@api.post("/temp-groups/{gid}/join")
async def join_temp(gid: int, user=Depends(get_user)):
    if not await db.one("SELECT id FROM temp_groups WHERE id=%s", (gid,)):
        raise HTTPException(404, "Group not found")
    uid = int(user["user_id"])
    if not await db.one("SELECT 1 AS x FROM temp_group_members WHERE group_id=%s AND user_id=%s", (gid, uid)):
        try:
            await db.run("INSERT INTO temp_group_members (group_id,user_id) VALUES (%s,%s)", (gid, uid))
        except Exception:      # double-click race: the composite PK already has this member
            pass
    return {"ok": True}


# ================================================================= Complaints
async def _complaints_out(rows: list) -> list:
    atts = await load_attachments("complaint", [r["id"] for r in rows])
    return [{
        "id": str(r["id"]), "subject": r["subject"], "body": r["body"], "author": r["author_name"],
        "real_author_id": str(r["real_author_id"]) if r["real_author_id"] is not None else None,
        "status": r["status"], "response": r["response"], "attachments": atts.get(r["id"], []),
        "created_at": iso(r["created_at"]), "responded_at": iso(r.get("responded_at")),
    } for r in rows]


@api.get("/complaints")
async def list_complaints(user=Depends(get_user)):
    if user["role"] in ("Administrator", "Convener"):
        rows = await db.all("SELECT * FROM complaints ORDER BY created_at DESC LIMIT 200")
    else:
        rows = await db.all("SELECT * FROM complaints WHERE real_author_id=%s ORDER BY created_at DESC LIMIT 200",
                            (int(user["user_id"]),))
    return await _complaints_out(rows)


@api.post("/complaints")
async def create_complaint(inp: ComplaintCreate, user=Depends(get_user)):
    attachments = validate_attachments(inp.attachments or [])
    async with db.transaction() as tx:
        cid = await tx.run(
            "INSERT INTO complaints (subject,body,author_name,real_author_id,status,response,created_at) "
            "VALUES (%s,%s,%s,%s,'Open','',%s)",
            (inp.subject.strip(), inp.body.strip(), user["name"], int(user["user_id"]), to_db(now_utc())),
        )
        await save_attachments(tx, "complaint", cid, attachments)
    return (await _complaints_out(await db.all("SELECT * FROM complaints WHERE id=%s", (cid,))))[0]


@api.post("/complaints/{cid}/respond")
async def respond_complaint(cid: int, inp: ComplaintRespond, user=Depends(get_user)):
    require_role(user, ["Administrator", "Convener"])
    n = await db.rowcount("UPDATE complaints SET response=%s, status='Responded', responded_at=%s WHERE id=%s",
                          (inp.response.strip(), to_db(now_utc()), cid))
    if not n:
        raise HTTPException(404, "Not found")
    return {"ok": True}


# ================================================================= Admin: users / roles
@api.get("/admin/users")
async def admin_list_users(user=Depends(get_user)):
    require_role(user, ["Administrator"])
    rows = await db.all(USER_SQL + "ORDER BY u.created_at DESC, u.id DESC LIMIT 1000")
    return [user_public(r) for r in rows]


@api.post("/admin/users/{uid}/role")
async def admin_set_role(uid: int, inp: RoleUpdate, user=Depends(get_user)):
    require_role(user, ["Administrator"])
    if inp.role not in ALLOWED_ROLES:
        raise HTTPException(400, "Invalid role")
    if not await db.one("SELECT id FROM users WHERE id=%s", (uid,)):
        raise HTTPException(404, "User not found")
    await db.run("UPDATE users SET role=%s WHERE id=%s", (inp.role, uid))
    r = await fetch_user("u.id=%s", (uid,))
    return {"ok": True, "user": user_public(r), "self_updated": user["user_id"] == str(uid)}


# ================================================================= Overview stats
@api.get("/stats/overview")
async def stats_overview(user=Depends(get_user)):
    dept_id = user["department_id"]
    if dept_id is not None:
        ann_count = (await db.one("SELECT COUNT(*) AS n FROM announcements WHERE department_id=%s", (dept_id,)))["n"]
        recent = await db.all(_ANN_SELECT + "WHERE a.department_id=%s ORDER BY a.created_at DESC LIMIT 3", (dept_id,))
    else:      # an administrator without a department sees the whole campus
        ann_count = (await db.one("SELECT COUNT(*) AS n FROM announcements"))["n"]
        recent = await db.all(_ANN_SELECT + "ORDER BY a.created_at DESC LIMIT 3")
    open_rows = await db.all("SELECT status, created_at FROM queries WHERE status IN ('Open','Answered')")
    escalated_alumni = sum(1 for q in open_rows if compute_stage(q["status"], q["created_at"]) == "alumni")
    recent_q = await db.all("SELECT id, author_encrypted_id, query_text, created_at FROM queries "
                            "ORDER BY created_at DESC LIMIT 3")
    clubs = (await db.one("SELECT COUNT(*) AS n FROM clubs"))["n"]

    def stamp(v):
        return (iso(v) or "")[:16].replace("T", " ")

    return {
        "announcements": ann_count,
        "open_queries": len(open_rows),
        "escalated_alumni": escalated_alumni,
        "clubs": clubs,
        "recent_announcements": [{"id": str(a["id"]), "title": a["title"], "author": a["author_name"],
                                  "time": stamp(a["created_at"])} for a in recent],
        "recent_queries": [{"id": str(q["id"]), "enc_id": q["author_encrypted_id"], "query": q["query_text"],
                            "time": stamp(q["created_at"])} for q in recent_q],
    }


# ================================================================= Escalation notifications
@api.get("/notifications/escalations")
async def escalations(user=Depends(get_user)):
    """Open queries currently at the user's escalation tier (Senior -> seniors, Alumni -> alumni,
    Professor / Administrator -> any escalated). Empty for other roles."""
    role = user["role"]
    if role == "Senior":
        target = "seniors"
    elif role == "Alumni":
        target = "alumni"
    elif role in ("Professor", "Administrator"):
        target = "any"
    else:
        return {"count": 0, "items": [], "tier": None}
    rows = await db.all(_Q_SELECT + "WHERE q.status IN ('Open','Answered') ORDER BY q.created_at DESC")
    items = []
    for q in rows:
        stage = compute_stage(q["status"], q["created_at"])
        if (target == "any" and stage in ("seniors", "alumni")) or stage == target:
            items.append({"id": str(q["id"]), "query": q["query_text"], "enc_id": q["author_encrypted_id"],
                          "topic": q["topic"], "department": q.get("department") or "", "stage": stage,
                          "created_at": iso(q["created_at"])})
    return {"count": len(items), "items": items, "tier": target}


# ================================================================= Professor analytics
@api.get("/analytics/professors")
async def professor_analytics(user=Depends(get_user)):
    profs = {}
    answers = await db.all(
        "SELECT a.author_name, a.created_at AS answered_at, q.topic, q.status, q.created_at AS asked_at "
        "FROM query_answers a JOIN queries q ON q.id = a.query_id WHERE a.role='Professor'")
    for a in answers:
        e = profs.setdefault(a["author_name"] or "Unknown", {"answers": 0, "hours": [], "topics": set(), "resolved": 0})
        e["answers"] += 1
        e["topics"].add(a["topic"] or "General")
        if a["status"] == "Resolved":
            e["resolved"] += 1
        e["hours"].append(max(0, (from_db(a["answered_at"]) - from_db(a["asked_at"])).total_seconds() / 3600.0))
    ranked = []
    for name, e in profs.items():
        hrs = e["hours"]
        ranked.append({"name": name, "answers": e["answers"],
                       "avg_response_hours": round(sum(hrs) / len(hrs), 2) if hrs else 0,
                       "fastest_response_hours": round(min(hrs), 2) if hrs else 0,
                       "topics": sorted(e["topics"]), "resolved_queries": e["resolved"]})
    ranked.sort(key=lambda x: (-x["answers"], x["avg_response_hours"]))

    threshold = now_utc() - timedelta(hours=48)
    open_rows = await db.all(
        "SELECT q.topic, q.created_at, d.name AS department, "
        "       (SELECT COUNT(*) FROM query_answers qa WHERE qa.query_id = q.id) AS n_answers "
        "FROM queries q LEFT JOIN departments d ON d.id = q.department_id WHERE q.status = 'Open'")
    unanswered_by_topic, stale = {}, 0
    for q in open_rows:
        if q["n_answers"] == 0 and from_db(q["created_at"]) < threshold:
            stale += 1
            key = f"{q.get('department') or '?'} · {q.get('topic') or 'General'}"
            unanswered_by_topic[key] = unanswered_by_topic.get(key, 0) + 1
    unanswered = sorted(({"topic": k, "count": v} for k, v in unanswered_by_topic.items()), key=lambda x: -x["count"])
    return {"professors": ranked, "unanswered_topics": unanswered[:10],
            "totals": {"professor_answers": len(answers), "open_queries": len(open_rows), "unanswered_48h": stale}}


# ================================================================= Weekly CR digest
@api.get("/digest/weekly")
async def weekly_digest(user=Depends(get_user)):
    """Monday-style digest for CR / DCR / Administrator: 7-day announcements, unresolved doubts,
    escalations and attendance defaulters (from members' personal trackers)."""
    if user["role"] not in ("CR", "DCR", "Administrator"):
        raise HTTPException(403, "Digest is available to CR, DCR and Administrator")
    dept_id = user["department_id"]
    scope_args = (dept_id,) if dept_id is not None else ()
    since = to_db(now_utc() - timedelta(days=7))

    ann_rows = await db.all(
        _ANN_SELECT + "WHERE a.created_at >= %s " + ("AND a.department_id = %s " if dept_id is not None else "")
        + "ORDER BY a.created_at DESC", (since,) + scope_args)
    ann = [{"id": str(a["id"]), "title": a["title"], "kind": a["kind"], "author": a["author_name"],
            "author_role": a["author_role"], "deadline": iso(a["deadline"]), "body": (a["body"] or "")[:280],
            "created_at": iso(a["created_at"])} for a in ann_rows]

    doubts, escalated = [], []
    for q in await db.all(
            "SELECT q.id, q.author_encrypted_id, q.topic, q.query_text, q.status, q.created_at, "
            "       (SELECT COUNT(*) FROM query_answers qa WHERE qa.query_id = q.id) AS n_answers "
            "FROM queries q WHERE q.status IN ('Open','Answered') "
            + ("AND q.department_id = %s " if dept_id is not None else "") + "ORDER BY q.created_at DESC",
            scope_args):
        stage = compute_stage(q["status"], q["created_at"])
        entry = {"id": str(q["id"]), "enc_id": q["author_encrypted_id"], "topic": q["topic"], "query": q["query_text"],
                 "answers": q["n_answers"], "stage": stage, "created_at": iso(q["created_at"])}
        doubts.append(entry)
        if stage in ("seniors", "alumni"):
            escalated.append(entry)

    defaulters = []
    for r in await db.all(
            "SELECT u.id, u.name, u.email, y.label AS year, SUM(s.attended) AS att, SUM(s.total) AS tot "
            "FROM users u JOIN self_attendance s ON s.user_id = u.id "
            "LEFT JOIN academic_years y ON y.id = u.year_id "
            "WHERE 1=1 " + ("AND u.department_id = %s " if dept_id is not None else "")
            + "GROUP BY u.id, u.name, u.email, y.label HAVING SUM(s.total) > 0", scope_args):
        pct = round(int(r["att"]) * 100 / int(r["tot"]))
        if pct < 75:
            defaulters.append({"name": r["name"], "email": r["email"], "year": r["year"] or "", "percent": pct,
                               "attended": int(r["att"]), "total": int(r["tot"])})
    defaulters.sort(key=lambda d: d["percent"])

    deadlines = []
    for a in ann:
        dt = parse_iso(a["deadline"])
        if dt and dt >= now_utc():
            deadlines.append({"title": a["title"], "when": a["deadline"], "kind": a["kind"]})
    deadlines.sort(key=lambda x: x["when"])

    return {
        "generated_at": iso(now_utc()), "week_ending": iso(now_utc()),
        "department": user["department"] if dept_id is not None else "All departments",
        "cr_name": user["name"],
        "summary": {"announcements_7d": len(ann), "open_doubts": len(doubts), "escalated": len(escalated),
                    "defaulters": len(defaulters), "upcoming_deadlines": len(deadlines)},
        "announcements": ann[:10], "doubts": doubts[:10], "escalated": escalated[:10],
        "deadlines": deadlines[:10], "defaulters": defaulters[:15],
    }


# ================================================================= WebSocket
@api.websocket("/ws")
async def campus_ws(websocket: WebSocket, token: str = ""):
    if not token:
        token = websocket.cookies.get("access_token") or ""
    row = await user_from_token(token) if token else None
    if not row:
        await websocket.close(code=1008)
        return
    user = user_public(row)
    await manager.connect(websocket, user)
    try:
        await websocket.send_text(json.dumps(
            {"type": "welcome", "payload": {"user_id": user["user_id"], "department": user.get("department")}}))
        while True:
            msg = await websocket.receive_text()
            if msg == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        await manager.disconnect(websocket)


@api.get("/ws/stats")
async def ws_stats(user=Depends(get_user)):
    return manager.stats()


# ================================================================= wiring
api.include_router(academics.router)
api.include_router(reports.router)
app.include_router(api)

_origins = [o.strip().rstrip("/") for o in os.environ.get("FRONTEND_URL", "").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins + ["http://localhost:3000"],   # FRONTEND_URL may hold several comma-separated URLs
    allow_origin_regex=os.environ.get("FRONTEND_ORIGIN_REGEX") or None,   # e.g. https://.*\.vercel\.app for previews
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
