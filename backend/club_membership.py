"""Club membership: request to join -> a club manager or the club's Head approves -> members see the archive
documents. Managers = Administrator / Convener / Professor; a member whose role is Head or Co-Head can also
approve, add members and upload documents for *their* club.
"""
import base64
import re
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field

import db
from common import get_user, iso, now_utc, to_db

router = APIRouter(prefix="/clubs")
GLOBAL_MANAGERS = ("Administrator", "Convener", "Professor")
LEADER_ROLES = ("Head", "Co-Head")
MEMBER_ROLES = ("Member", "Core", "Co-Head", "Head")
MAX_DOC_BYTES = 4 * 1024 * 1024
MAX_DOCS_PER_CLUB = 60


class JoinIn(BaseModel):
    message: str = Field(default="", max_length=300)


class RoleIn(BaseModel):
    role: str


class AddByRollIn(BaseModel):
    roll_nos: List[str] = Field(max_length=300)
    role: str = "Member"


class DocFile(BaseModel):
    name: str = Field(max_length=160)
    mime: str = Field(default="application/octet-stream", max_length=100)
    data: str


class DocIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=500)
    file: DocFile


def _safe(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9._ -]", "_", name.split("/")[-1].split("\\")[-1])[:120] or "file"


async def _club(club_id: int) -> dict:
    c = await db.one("SELECT id, name FROM clubs WHERE id=%s", (club_id,))
    if not c:
        raise HTTPException(404, "Club not found")
    return c


async def membership(user: dict, club_id: int) -> dict:
    """{'member': bool, 'role': str|None, 'manage': bool}"""
    m = await db.one("SELECT role FROM club_members WHERE club_id=%s AND user_id=%s", (club_id, int(user["user_id"])))
    role = m["role"] if m else None
    return {"member": bool(m), "role": role, "global": user["role"] in GLOBAL_MANAGERS,
            "manage": user["role"] in GLOBAL_MANAGERS or role in LEADER_ROLES}


async def _need_manage(user: dict, club_id: int) -> dict:
    await _club(club_id)
    st = await membership(user, club_id)
    if not st["manage"]:
        raise HTTPException(403, "Only the club's managers or Head can do that")
    return st


async def _need_access(user: dict, club_id: int) -> dict:
    await _club(club_id)
    st = await membership(user, club_id)
    if not (st["member"] or st["manage"]):
        raise HTTPException(403, "Join the club to see this")
    return st


async def attach_membership(clubs: list, user: dict) -> list:
    """Adds my_status / my_role / can_manage / member_count (/ pending_count for managers) to a club list."""
    if not clubs:
        return clubs
    ids = tuple(c["id"] for c in clubs)
    marks = ",".join(["%s"] * len(ids))
    me = int(user["user_id"])
    mine = {r["club_id"]: r["role"] for r in await db.all(f"SELECT club_id, role FROM club_members WHERE user_id=%s AND club_id IN ({marks})", (me,) + ids)}
    pend = {r["club_id"] for r in await db.all(f"SELECT club_id FROM club_join_requests WHERE user_id=%s AND club_id IN ({marks})", (me,) + ids)}
    counts = {r["club_id"]: r["n"] for r in await db.all(f"SELECT club_id, COUNT(*) AS n FROM club_members WHERE club_id IN ({marks}) GROUP BY club_id", ids)}
    waiting = {r["club_id"]: r["n"] for r in await db.all(f"SELECT club_id, COUNT(*) AS n FROM club_join_requests WHERE club_id IN ({marks}) GROUP BY club_id", ids)}
    for c in clubs:
        role = mine.get(c["id"])
        manage = user["role"] in GLOBAL_MANAGERS or role in LEADER_ROLES
        c.update({"my_status": "member" if role else ("pending" if c["id"] in pend else "none"), "my_role": role,
                  "can_manage": manage, "member_count": int(counts.get(c["id"], 0)),
                  "pending_count": int(waiting.get(c["id"], 0)) if manage else 0})
    return clubs


# ------------------------------------------------------------------ joining
@router.post("/{club_id}/join")
async def request_join(club_id: int, inp: JoinIn, user=Depends(get_user)):
    await _club(club_id)
    st = await membership(user, club_id)
    if st["member"]:
        raise HTTPException(400, "You are already a member")
    me = int(user["user_id"])
    if not await db.one("SELECT 1 AS x FROM club_join_requests WHERE club_id=%s AND user_id=%s", (club_id, me)):
        await db.run("INSERT INTO club_join_requests (club_id,user_id,user_name,message,created_at) VALUES (%s,%s,%s,%s,%s)",
                     (club_id, me, user["name"], inp.message.strip(), to_db(now_utc())))
    return {"ok": True, "status": "pending"}


@router.delete("/{club_id}/join")
async def cancel_or_leave(club_id: int, user=Depends(get_user)):
    """Withdraw a pending request, or leave the club."""
    me = int(user["user_id"])
    await db.run("DELETE FROM club_join_requests WHERE club_id=%s AND user_id=%s", (club_id, me))
    await db.run("DELETE FROM club_members WHERE club_id=%s AND user_id=%s", (club_id, me))
    return {"ok": True, "status": "none"}


@router.get("/{club_id}/requests")
async def list_requests(club_id: int, user=Depends(get_user)):
    await _need_manage(user, club_id)
    rows = await db.all("SELECT r.user_id, r.user_name, r.message, r.created_at, u.roll_no, d.name AS department, y.label AS year "
                        "FROM club_join_requests r JOIN users u ON u.id = r.user_id LEFT JOIN departments d ON d.id = u.department_id "
                        "LEFT JOIN academic_years y ON y.id = u.year_id WHERE r.club_id=%s ORDER BY r.created_at", (club_id,))
    return [{"user_id": r["user_id"], "name": r["user_name"], "message": r["message"], "roll_no": r["roll_no"] or "",
             "department": r["department"] or "", "year": r["year"] or "", "created_at": iso(r["created_at"])} for r in rows]


@router.post("/{club_id}/requests/{uid}/{decision}")
async def decide(club_id: int, uid: int, decision: str, user=Depends(get_user)):
    if decision not in ("approve", "decline"):
        raise HTTPException(404, "Not found")
    await _need_manage(user, club_id)
    if not await db.one("SELECT 1 AS x FROM club_join_requests WHERE club_id=%s AND user_id=%s", (club_id, uid)):
        raise HTTPException(404, "No such request")
    async with db.transaction() as tx:
        await tx.run("DELETE FROM club_join_requests WHERE club_id=%s AND user_id=%s", (club_id, uid))
        if decision == "approve" and not await tx.one("SELECT 1 AS x FROM club_members WHERE club_id=%s AND user_id=%s", (club_id, uid)):
            await tx.run("INSERT INTO club_members (club_id,user_id,role,joined_at) VALUES (%s,%s,'Member',%s)", (club_id, uid, to_db(now_utc())))
    return {"ok": True}


# ------------------------------------------------------------------ members
@router.get("/{club_id}/members")
async def members(club_id: int, user=Depends(get_user)):
    await _need_access(user, club_id)
    rows = await db.all("SELECT u.id, u.name, u.roll_no, m.role, m.joined_at, d.name AS department, y.label AS year "
                        "FROM club_members m JOIN users u ON u.id = m.user_id LEFT JOIN departments d ON d.id = u.department_id "
                        "LEFT JOIN academic_years y ON y.id = u.year_id WHERE m.club_id=%s ORDER BY m.role DESC, u.name", (club_id,))
    order = {"Head": 0, "Co-Head": 1, "Core": 2, "Member": 3}
    out = [{"user_id": r["id"], "name": r["name"], "roll_no": r["roll_no"] or "", "role": r["role"],
            "department": r["department"] or "", "year": r["year"] or "", "joined_at": iso(r["joined_at"])} for r in rows]
    return sorted(out, key=lambda m: (order.get(m["role"], 9), m["name"]))


@router.post("/{club_id}/members/{uid}/role")
async def set_role(club_id: int, uid: int, inp: RoleIn, user=Depends(get_user)):
    st = await _need_manage(user, club_id)
    if not st["global"]:
        raise HTTPException(403, "Only an Administrator, Convener or Professor can change roles")
    if inp.role not in MEMBER_ROLES:
        raise HTTPException(400, f"Role must be one of {', '.join(MEMBER_ROLES)}")
    if not await db.rowcount("UPDATE club_members SET role=%s WHERE club_id=%s AND user_id=%s", (inp.role, club_id, uid)):
        raise HTTPException(404, "Not a member")
    return {"ok": True}


@router.delete("/{club_id}/members/{uid}")
async def remove_member(club_id: int, uid: int, user=Depends(get_user)):
    await _need_manage(user, club_id)
    await db.run("DELETE FROM club_members WHERE club_id=%s AND user_id=%s", (club_id, uid))
    return {"ok": True}


@router.post("/{club_id}/members/add-by-roll")
async def add_by_roll(club_id: int, inp: AddByRollIn, user=Depends(get_user)):
    """Add known students straight from a pasted list of roll / admission numbers (no request needed)."""
    st = await _need_manage(user, club_id)
    role = inp.role if inp.role in MEMBER_ROLES else "Member"
    if role in LEADER_ROLES and not st["global"]:
        raise HTTPException(403, "Only an Administrator, Convener or Professor can appoint a Head")
    rolls = sorted({r.strip().upper() for r in inp.roll_nos if r.strip()})
    added, already, missing = [], [], []
    for roll in rolls:
        u = await db.one("SELECT id FROM users WHERE UPPER(roll_no)=%s", (roll,))
        if not u:
            missing.append(roll)
        elif await db.one("SELECT 1 AS x FROM club_members WHERE club_id=%s AND user_id=%s", (club_id, u["id"])):
            already.append(roll)
        else:
            await db.run("DELETE FROM club_join_requests WHERE club_id=%s AND user_id=%s", (club_id, u["id"]))
            await db.run("INSERT INTO club_members (club_id,user_id,role,joined_at) VALUES (%s,%s,%s,%s)", (club_id, u["id"], role, to_db(now_utc())))
            added.append(roll)
    return {"ok": True, "added": added, "already_members": already, "not_found": missing}


# ------------------------------------------------------------------ archive documents
@router.get("/{club_id}/documents")
async def list_documents(club_id: int, user=Depends(get_user)):
    await _need_access(user, club_id)
    rows = await db.all("SELECT id, title, description, file_name, mime, size, uploaded_by_name, created_at FROM club_documents "
                        "WHERE club_id=%s ORDER BY id DESC", (club_id,))
    return [{"id": r["id"], "title": r["title"], "description": r["description"], "file_name": r["file_name"],
             "mime": r["mime"], "size": r["size"], "uploaded_by": r["uploaded_by_name"], "created_at": iso(r["created_at"])} for r in rows]


@router.post("/{club_id}/documents")
async def upload_document(club_id: int, inp: DocIn, user=Depends(get_user)):
    await _need_manage(user, club_id)
    try:
        raw = base64.b64decode(inp.file.data, validate=True)
    except Exception:                                       # noqa: BLE001
        raise HTTPException(400, "File is not valid base64")
    if len(raw) > MAX_DOC_BYTES:
        raise HTTPException(413, "Documents are limited to 4 MB")
    if (await db.one("SELECT COUNT(*) AS n FROM club_documents WHERE club_id=%s", (club_id,)))["n"] >= MAX_DOCS_PER_CLUB:
        raise HTTPException(413, "This club has reached its limit of 60 documents")
    did = await db.run(
        "INSERT INTO club_documents (club_id,title,description,file_name,mime,size,data,uploaded_by,uploaded_by_name,created_at) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        (club_id, inp.title.strip(), inp.description.strip(), _safe(inp.file.name), inp.file.mime[:100], len(raw), inp.file.data,
         int(user["user_id"]), user["name"], to_db(now_utc())))
    return {"ok": True, "id": did}


@router.get("/{club_id}/documents/{doc_id}/file")
async def download_document(club_id: int, doc_id: int, user=Depends(get_user)):
    await _need_access(user, club_id)
    r = await db.one("SELECT file_name, mime, data FROM club_documents WHERE id=%s AND club_id=%s", (doc_id, club_id))
    if not r:
        raise HTTPException(404, "Document not found")
    return Response(content=base64.b64decode(r["data"]), media_type=r["mime"],
                    headers={"Content-Disposition": f'attachment; filename="{_safe(r["file_name"])}"'})


@router.delete("/{club_id}/documents/{doc_id}")
async def delete_document(club_id: int, doc_id: int, user=Depends(get_user)):
    await _need_manage(user, club_id)
    await db.run("DELETE FROM club_documents WHERE id=%s AND club_id=%s", (doc_id, club_id))
    return {"ok": True}
