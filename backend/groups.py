"""Temporary groups: private, request-to-join chat rooms that delete themselves (messages and files included).

Privacy model
  * Groups are not listed to outsiders. You find one by typing its exact name (the "keyword");
    the answer is always the same whether or not it exists, so names cannot be probed.
  * The creator approves or declines every request.
  * Members chat under their real account names and can share files (2 MB each, 30 MB per group).
  * When expires_at passes, the group row is deleted and ON DELETE CASCADE removes members, requests,
    messages and files. Members can download a ZIP of the chat + files at any time (and are nudged to).
"""
import asyncio
import base64
import io
import re
import zipfile
from datetime import timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field

import db
from common import from_db, get_user, iso, now_utc, to_db

router = APIRouter(prefix="/temp-groups")
MAX_FILE_BYTES = 2 * 1024 * 1024
GROUP_FILE_BUDGET = 30 * 1024 * 1024
MAX_PENDING_PER_USER = 10
MAX_LIFETIME = timedelta(days=30)
GENERIC_REQUEST = {"ok": True, "message": "If a group with that name exists, its creator has been asked. "
                                          "It will appear here once they accept."}


class GroupCreate(BaseModel):
    name: str = Field(min_length=3, max_length=60)
    hours: int = Field(default=24, ge=1, le=24 * 30)


class RequestByName(BaseModel):
    name: str = Field(min_length=1, max_length=60)


class FileIn(BaseModel):
    name: str = Field(default="file", max_length=120)
    mime: str = Field(default="application/octet-stream", max_length=100)
    data: str                                              # base64


class MessageIn(BaseModel):
    body: str = Field(default="", max_length=2000)
    file: Optional[FileIn] = None


class ExtendIn(BaseModel):
    hours: int = Field(ge=1, le=24 * 30)


# ------------------------------------------------------------------ helpers
async def purge_expired():
    await db.run("DELETE FROM temp_groups WHERE expires_at < %s", (to_db(now_utc()),))


async def purge_loop(every: int = 300):
    """Background sweep so expired chats disappear even when nobody is calling the API."""
    while True:
        try:
            await purge_expired()
        except Exception:                                   # noqa: BLE001 - keep sweeping
            pass
        await asyncio.sleep(every)


async def _group(gid: int) -> dict:
    await purge_expired()
    g = await db.one("SELECT id, name, creator_id, creator_name, created_at, expires_at FROM temp_groups WHERE id=%s", (gid,))
    if not g:
        raise HTTPException(404, "Group not found (it may have expired)")
    return g


async def _member_group(gid: int, user: dict) -> dict:
    g = await _group(gid)
    if not await db.one("SELECT 1 AS x FROM temp_group_members WHERE group_id=%s AND user_id=%s", (gid, int(user["user_id"]))):
        raise HTTPException(404, "Group not found (it may have expired)")      # same answer for outsiders
    return g


def _is_creator(g: dict, user: dict) -> bool:
    return g["creator_id"] is not None and g["creator_id"] == int(user["user_id"])


def _safe_name(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9._ -]", "_", name.split("/")[-1].split("\\")[-1])[:100] or "file"


def _msg_out(r: dict) -> dict:
    has_file = r.get("file_name") is not None
    return {"id": r["id"], "user_id": str(r["user_id"]) if r["user_id"] is not None else None, "user_name": r["user_name"],
            "body": r["body"], "created_at": iso(r["created_at"]),
            "file": {"name": r["file_name"], "mime": r["file_mime"], "size": r["file_size"]} if has_file else None}


_MSG_COLS = "id, user_id, user_name, body, file_name, file_mime, file_size, created_at"


# ------------------------------------------------------------------ list / create / find
@router.get("")
async def my_groups(user=Depends(get_user)):
    await purge_expired()
    me = int(user["user_id"])
    rows = await db.all(
        "SELECT g.id, g.name, g.creator_id, g.creator_name, g.created_at, g.expires_at, "
        "  (SELECT COUNT(*) FROM temp_group_members m WHERE m.group_id = g.id) AS member_count, "
        "  (SELECT COUNT(*) FROM temp_group_requests r WHERE r.group_id = g.id) AS pending "
        "FROM temp_groups g JOIN temp_group_members mm ON mm.group_id = g.id AND mm.user_id = %s ORDER BY g.expires_at", (me,))
    mine = [{"id": g["id"], "name": g["name"], "creator_name": g["creator_name"],
             "creator_id": str(g["creator_id"]) if g["creator_id"] is not None else None,
             "is_creator": g["creator_id"] == me, "member_count": int(g["member_count"]),
             "pending_requests": int(g["pending"]) if g["creator_id"] == me else 0,
             "created_at": iso(g["created_at"]), "expires_at": iso(g["expires_at"])} for g in rows]
    waiting = await db.all("SELECT g.name FROM temp_group_requests r JOIN temp_groups g ON g.id = r.group_id "
                           "WHERE r.user_id=%s ORDER BY r.created_at", (me,))
    return {"groups": mine, "my_requests": [w["name"] for w in waiting]}


@router.post("")
async def create_group(inp: GroupCreate, user=Depends(get_user)):
    await purge_expired()
    name = " ".join(inp.name.split())
    if await db.one("SELECT id FROM temp_groups WHERE LOWER(name)=LOWER(%s)", (name,)):
        raise HTTPException(409, "A live group already uses that name — pick another keyword.")
    now = now_utc()
    me = int(user["user_id"])
    async with db.transaction() as tx:
        gid = await tx.run("INSERT INTO temp_groups (name,creator_id,creator_name,created_at,expires_at) VALUES (%s,%s,%s,%s,%s)",
                           (name, me, user["name"], to_db(now), to_db(now + timedelta(hours=inp.hours))))
        await tx.run("INSERT INTO temp_group_members (group_id,user_id) VALUES (%s,%s)", (gid, me))
    return {"ok": True, "id": gid, "name": name, "expires_at": iso(now + timedelta(hours=inp.hours))}


@router.post("/request")
async def request_by_name(inp: RequestByName, user=Depends(get_user)):
    await purge_expired()
    me = int(user["user_id"])
    g = await db.one("SELECT id FROM temp_groups WHERE LOWER(name)=LOWER(%s)", (" ".join(inp.name.split()),))
    if g and not await db.one("SELECT 1 AS x FROM temp_group_members WHERE group_id=%s AND user_id=%s", (g["id"], me)):
        n = (await db.one("SELECT COUNT(*) AS n FROM temp_group_requests WHERE user_id=%s", (me,)))["n"]
        if n >= MAX_PENDING_PER_USER:
            raise HTTPException(429, "You already have 10 pending requests.")
        if not await db.one("SELECT 1 AS x FROM temp_group_requests WHERE group_id=%s AND user_id=%s", (g["id"], me)):
            await db.run("INSERT INTO temp_group_requests (group_id,user_id,user_name,created_at) VALUES (%s,%s,%s,%s)",
                         (g["id"], me, user["name"], to_db(now_utc())))
    return GENERIC_REQUEST


# ------------------------------------------------------------------ creator tools
@router.get("/{gid}/requests")
async def list_requests(gid: int, user=Depends(get_user)):
    g = await _member_group(gid, user)
    if not _is_creator(g, user):
        raise HTTPException(403, "Only the creator can see join requests")
    rows = await db.all("SELECT r.user_id, r.user_name, r.created_at, u.department_id, d.name AS department, u.roll_no "
                        "FROM temp_group_requests r JOIN users u ON u.id = r.user_id "
                        "LEFT JOIN departments d ON d.id = u.department_id WHERE r.group_id=%s ORDER BY r.created_at", (gid,))
    return [{"user_id": str(r["user_id"]), "name": r["user_name"], "department": r["department"] or "",
             "roll_no": r["roll_no"] or "", "created_at": iso(r["created_at"])} for r in rows]


@router.post("/{gid}/requests/{uid}/{decision}")
async def decide_request(gid: int, uid: int, decision: str, user=Depends(get_user)):
    if decision not in ("approve", "decline"):
        raise HTTPException(404, "Not found")
    g = await _member_group(gid, user)
    if not _is_creator(g, user):
        raise HTTPException(403, "Only the creator can decide")
    if not await db.one("SELECT 1 AS x FROM temp_group_requests WHERE group_id=%s AND user_id=%s", (gid, uid)):
        raise HTTPException(404, "No such request")
    async with db.transaction() as tx:
        await tx.run("DELETE FROM temp_group_requests WHERE group_id=%s AND user_id=%s", (gid, uid))
        if decision == "approve":
            await tx.run("INSERT INTO temp_group_members (group_id,user_id) VALUES (%s,%s)", (gid, uid))
    return {"ok": True}


@router.post("/{gid}/extend")
async def extend(gid: int, inp: ExtendIn, user=Depends(get_user)):
    g = await _member_group(gid, user)
    if not _is_creator(g, user):
        raise HTTPException(403, "Only the creator can extend the group")
    new_end = min(from_db(g["expires_at"]) + timedelta(hours=inp.hours), from_db(g["created_at"]) + MAX_LIFETIME)
    await db.run("UPDATE temp_groups SET expires_at=%s WHERE id=%s", (to_db(new_end), gid))
    return {"ok": True, "expires_at": iso(new_end)}


@router.delete("/{gid}")
async def delete_group(gid: int, user=Depends(get_user)):
    g = await _member_group(gid, user)
    if not _is_creator(g, user):
        raise HTTPException(403, "Only the creator can delete the group")
    await db.run("DELETE FROM temp_groups WHERE id=%s", (gid,))
    return {"ok": True}


@router.delete("/{gid}/members/{uid}")
async def remove_member(gid: int, uid: int, user=Depends(get_user)):
    """Leave (uid = you) or, as creator, remove someone."""
    g = await _member_group(gid, user)
    me = int(user["user_id"])
    if uid != me and not _is_creator(g, user):
        raise HTTPException(403, "Only the creator can remove other members")
    if uid == g["creator_id"]:
        raise HTTPException(400, "The creator cannot leave — delete the group instead")
    await db.run("DELETE FROM temp_group_members WHERE group_id=%s AND user_id=%s", (gid, uid))
    return {"ok": True}


# ------------------------------------------------------------------ members + chat
@router.get("/{gid}/members")
async def members(gid: int, user=Depends(get_user)):
    g = await _member_group(gid, user)
    rows = await db.all("SELECT u.id, u.name, u.roll_no, d.name AS department FROM temp_group_members m "
                        "JOIN users u ON u.id = m.user_id LEFT JOIN departments d ON d.id = u.department_id "
                        "WHERE m.group_id=%s ORDER BY u.name", (gid,))
    return {"group": {"id": g["id"], "name": g["name"], "expires_at": iso(g["expires_at"]), "is_creator": _is_creator(g, user)},
            "members": [{"user_id": str(r["id"]), "name": r["name"], "roll_no": r["roll_no"] or "",
                         "department": r["department"] or "", "is_creator": r["id"] == g["creator_id"]} for r in rows]}


@router.get("/{gid}/messages")
async def messages(gid: int, after: int = 0, user=Depends(get_user)):
    await _member_group(gid, user)
    rows = await db.all(f"SELECT {_MSG_COLS} FROM temp_group_messages WHERE group_id=%s AND id > %s ORDER BY id DESC LIMIT 200", (gid, after))
    return [_msg_out(r) for r in reversed(rows)]


@router.post("/{gid}/messages")
async def post_message(gid: int, inp: MessageIn, user=Depends(get_user)):
    await _member_group(gid, user)
    body = inp.body.strip()
    if not body and not inp.file:
        raise HTTPException(400, "Write a message or attach a file")
    f_name = f_mime = f_data = None
    f_size = None
    if inp.file:
        try:
            raw = base64.b64decode(inp.file.data, validate=True)
        except Exception:                                   # noqa: BLE001
            raise HTTPException(400, "Attachment is not valid base64")
        if len(raw) > MAX_FILE_BYTES:
            raise HTTPException(413, "Files are limited to 2 MB")
        used = (await db.one("SELECT COALESCE(SUM(file_size),0) AS n FROM temp_group_messages WHERE group_id=%s", (gid,)))["n"]
        if int(used) + len(raw) > GROUP_FILE_BUDGET:
            raise HTTPException(413, "This group has used up its 30 MB of shared files")
        f_name, f_mime, f_data, f_size = _safe_name(inp.file.name), inp.file.mime[:100], inp.file.data, len(raw)
    mid = await db.run(
        "INSERT INTO temp_group_messages (group_id,user_id,user_name,body,file_name,file_mime,file_size,file_data,created_at) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        (gid, int(user["user_id"]), user["name"], body, f_name, f_mime, f_size, f_data, to_db(now_utc())))
    return _msg_out(await db.one(f"SELECT {_MSG_COLS} FROM temp_group_messages WHERE id=%s", (mid,)))


@router.get("/{gid}/messages/{mid}/file")
async def message_file(gid: int, mid: int, user=Depends(get_user)):
    await _member_group(gid, user)
    r = await db.one("SELECT file_name, file_mime, file_data FROM temp_group_messages WHERE id=%s AND group_id=%s AND file_name IS NOT NULL", (mid, gid))
    if not r:
        raise HTTPException(404, "File not found")
    return Response(content=base64.b64decode(r["file_data"]), media_type=r["file_mime"] or "application/octet-stream",
                    headers={"Content-Disposition": f'attachment; filename="{_safe_name(r["file_name"])}"'})


@router.get("/{gid}/export")
async def export_group(gid: int, user=Depends(get_user)):
    """ZIP with chat.txt and every shared file — for saving locally before the group is deleted."""
    g = await _member_group(gid, user)
    rows = await db.all("SELECT id, user_name, body, file_name, file_data, created_at FROM temp_group_messages WHERE group_id=%s ORDER BY id", (gid,))
    lines = [f"Group: {g['name']}", f"Deleted automatically at: {iso(g['expires_at'])}", ""]
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for r in rows:
            line = f"[{iso(r['created_at'])}] {r['user_name']}: {r['body']}".rstrip()
            if r["file_name"]:
                fname = f"files/{r['id']}_{_safe_name(r['file_name'])}"
                z.writestr(fname, base64.b64decode(r["file_data"]))
                line += f"  [file: {fname}]"
            lines.append(line)
        z.writestr("chat.txt", "\n".join(lines) + "\n")
    return Response(content=buf.getvalue(), media_type="application/zip",
                    headers={"Content-Disposition": f'attachment; filename="{_safe_name(g["name"])}-chat.zip"'})
