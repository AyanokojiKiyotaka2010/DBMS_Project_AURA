"""Group chat + club membership logic on sqlite (no server). FastAPI/pydantic are stubbed when not installed.

Run:  python3 tests/test_social_sqlite.py     (or pytest -n 0 tests/test_social_sqlite.py)
"""
import asyncio
import base64
import io
import os
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, os.path.dirname(HERE)]
try:
    import fastapi, pydantic, bcrypt  # noqa: F401
except ImportError:                      # lightweight stand-ins, enough for calling the endpoint functions directly
    sys.path.append(os.path.join(HERE, "stubs"))

import db  # noqa: E402
import sqlite_db  # noqa: E402
from fastapi import HTTPException  # noqa: E402

_LOOP = asyncio.new_event_loop()


def run(coro):
    return _LOOP.run_until_complete(coro)


def expect(code, coro):
    try:
        run(coro)
    except HTTPException as e:
        assert e.status_code == code, (code, e.status_code, e.detail)
        return
    raise AssertionError(f"expected HTTP {code}")


def make_user(conn):
    def U(name, role="Student", **kw):
        uid = conn.run("INSERT INTO users (name,email,password_hash,role,roll_no,created_at) VALUES (%s,%s,'x',%s,%s,'2026-01-01 00:00:00')",
                       (name, name.lower() + "@x.edu", role, kw.get("roll")))
        return {"user_id": str(uid), "name": name, "role": role}
    return U


def test_temp_groups_privacy_chat_export_and_expiry():
    import groups
    conn = sqlite_db.install(db)
    U = make_user(conn)
    G=groups
    cre, bob, eve = U("Creator"), U("Bob"), U("Eve")
    g=run(G.create_group(G.GroupCreate(name="Nova Team", hours=24), cre)); gid=g["id"]
    expect(409, G.create_group(G.GroupCreate(name="nova team", hours=2), bob))
    assert run(G.my_groups(bob))["groups"]==[]
    r1=run(G.request_by_name(G.RequestByName(name="NOVA team"), bob)); r2=run(G.request_by_name(G.RequestByName(name="no such group"), eve))
    assert r1==r2
    assert [x["name"] for x in run(G.list_requests(gid, cre))]==["Bob"]
    expect(404, G.messages(gid, 0, bob))
    expect(404, G.decide_request(gid, int(bob["user_id"]), "approve", eve))
    expect(404, G.list_requests(gid, eve))
    run(G.decide_request(gid, int(bob["user_id"]), "approve", cre))
    assert run(G.my_groups(bob))["groups"][0]["name"]=="Nova Team" and run(G.my_groups(cre))["groups"][0]["pending_requests"]==0
    png=base64.b64encode(b"\x89PNG-test").decode()
    m=run(G.post_message(gid, G.MessageIn(body="hello team", file=G.FileIn(name="../../pic.png", mime="image/png", data=png)), bob))
    assert m["file"]["name"]=="pic.png" and m["user_name"]=="Bob"
    assert [x["body"] for x in run(G.messages(gid, 0, cre))]==["hello team"] and run(G.messages(gid, m["id"], cre))==[]
    assert run(G.message_file(gid, m["id"], cre)).content==b"\x89PNG-test"
    expect(413, G.post_message(gid, G.MessageIn(body="", file=G.FileIn(name="big", mime="x", data=base64.b64encode(b"0"*(2*1024*1024+1)).decode())), bob))
    expect(400, G.post_message(gid, G.MessageIn(body="  "), bob))
    z=zipfile.ZipFile(io.BytesIO(run(G.export_group(gid, bob)).content)); assert set(z.namelist())=={"chat.txt", f"files/{m['id']}_pic.png"} and b"hello team" in z.read("chat.txt")
    run(G.extend(gid, G.ExtendIn(hours=5), cre))
    expect(403, G.extend(gid, G.ExtendIn(hours=5), bob))
    expect(400, G.remove_member(gid, int(cre["user_id"]), cre))
    expect(403, G.remove_member(gid, int(eve["user_id"]), bob))
    run(G.remove_member(gid, int(bob["user_id"]), bob))
    expect(404, G.messages(gid, 0, bob))
    conn.run("UPDATE temp_groups SET expires_at='2000-01-01 00:00:00'")
    expect(404, G.messages(gid, 0, cre))
    assert conn.all("SELECT count(*) n FROM temp_group_messages")[0]["n"]==0 and conn.all("SELECT count(*) n FROM temp_group_members")[0]["n"]==0

def test_club_join_documents_and_heads():
    import club_membership as cm
    conn = sqlite_db.install(db)
    U = make_user(conn)
    conn.run("INSERT INTO clubs (name,description,created_at) VALUES ('ACM','d','2026-01-01 00:00:00')"); cid=1
    prof=U("Prof","Professor"); stu=U("Stu",roll="U25CS001"); head=U("Hed",roll="U24CS002"); other=U("Oth")
    conn.run("INSERT INTO users (name,email,password_hash,role,roll_no,created_at) VALUES ('Placeholder','u23cs003@import.invalid','!','Student','U23CS003','2026-01-01 00:00:00')")
    assert run(cm.request_join(cid, cm.JoinIn(message="pls"), stu))["status"]=="pending"
    expect(403, cm.list_requests(cid, other)); expect(403, cm.list_documents(cid, stu))
    rows=run(cm.attach_membership([{"id":cid}], stu)); assert rows[0]["my_status"]=="pending" and rows[0]["can_manage"] is False
    res=run(cm.add_by_roll(cid, cm.AddByRollIn(roll_nos=["u24cs002","U99ZZ999","U23CS003"], role="Head"), prof))
    assert res["added"]==["U23CS003","U24CS002"] and res["not_found"]==["U99ZZ999"], res
    run(cm.decide(cid, int(stu["user_id"]), "approve", prof))
    assert run(cm.attach_membership([{"id":cid}], stu))[0]["my_status"]=="member"
    head_user={**head,"role":"Student"}
    assert run(cm.attach_membership([{"id":cid}], head_user))[0]["can_manage"] is True
    expect(403, cm.set_role(cid, int(stu["user_id"]), cm.RoleIn(role="Head"), head_user))
    run(cm.set_role(cid, int(stu["user_id"]), cm.RoleIn(role="Core"), prof))
    d=run(cm.upload_document(cid, cm.DocIn(title="Report 2025", description="", file=cm.DocFile(name="r.pdf", mime="application/pdf", data=base64.b64encode(b"%PDF-1").decode())), head_user))
    expect(403, cm.upload_document(cid, cm.DocIn(title="x", description="", file=cm.DocFile(name="r", mime="a/b", data="QQ==")), stu))
    assert run(cm.list_documents(cid, stu))[0]["title"]=="Report 2025" and run(cm.download_document(cid, d["id"], stu)).content==b"%PDF-1"
    assert [m["role"] for m in run(cm.members(cid, stu))]==["Head","Head","Core"], [m["role"] for m in run(cm.members(cid, stu))]
    run(cm.cancel_or_leave(cid, stu)); expect(403, cm.list_documents(cid, stu))

if __name__ == "__main__":
    test_temp_groups_privacy_chat_export_and_expiry()
    print("ok   groups")
    test_club_join_documents_and_heads()
    print("ok   clubs")
