"""AURA Campus Backend API tests."""
import os
import uuid
import pytest
import requests

BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/") if os.environ.get("REACT_APP_BACKEND_URL") else None
# Fall back to reading frontend .env
if not BASE:
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                BASE = line.split("=", 1)[1].strip().rstrip("/")
API = f"{BASE}/api"

CREDS = {
    "admin": ("admin@campus.edu", "admin123"),
    "cr": ("cr@campus.edu", "cr12345"),
    "dcr": ("dcr@campus.edu", "dcr12345"),
    "prof": ("prof@campus.edu", "prof12345"),
    "senior": ("senior@campus.edu", "senior12345"),
    "alumni": ("alumni@campus.edu", "alumni12345"),
    "student": ("student@campus.edu", "student123"),
}


def _login(persona):
    email, pw = CREDS[persona]
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": email, "password": pw})
    assert r.status_code == 200, f"login {persona}: {r.status_code} {r.text}"
    return s, r.json()["user"]


# ---------- Auth ----------
def test_seeded_logins_all_roles():
    for p in CREDS:
        s, u = _login(p)
        assert u["email"] == CREDS[p][0]

def test_me_endpoint():
    s, u = _login("student")
    r = s.get(f"{API}/auth/me")
    assert r.status_code == 200
    assert r.json()["email"] == "student@campus.edu"

def test_login_wrong_password():
    r = requests.post(f"{API}/auth/login", json={"email": "student@campus.edu", "password": "wrong"})
    assert r.status_code == 401

def test_register_new_user_then_login():
    email = f"test_{uuid.uuid4().hex[:8]}@t.edu"
    r = requests.post(f"{API}/auth/register", json={
        "name": "TEST User", "email": email, "password": "pw12345",
        "role": "Student"
    })
    assert r.status_code == 200
    assert r.json()["user"]["email"] == email
    # Login again
    r2 = requests.post(f"{API}/auth/login", json={"email": email, "password": "pw12345"})
    assert r2.status_code == 200

def test_self_register_cannot_pick_privileged_role():
    r = requests.post(f"{API}/auth/register", json={
        "name": "TEST Sneaky", "email": f"test_{uuid.uuid4().hex[:8]}@t.edu", "password": "pw12345", "role": "Professor"})
    assert r.status_code == 400

def test_unauth_endpoints_return_401():
    r = requests.get(f"{API}/announcements")
    assert r.status_code == 401


# ---------- Announcements ----------
def test_cr_can_post_announcement_and_list_shows_it():
    s, _ = _login("cr")
    title = f"TEST Ann {uuid.uuid4().hex[:6]}"
    r = s.post(f"{API}/announcements", json={
        "title": title, "body": "hello", "kind": "general",
        "department": "Computer Science", "year": "3rd Year"
    })
    assert r.status_code == 200
    ann = r.json()
    assert ann["title"] == title
    # verify persistence via GET
    lst = s.get(f"{API}/announcements").json()
    assert any(a["title"] == title for a in lst)

def test_student_cannot_post_announcement():
    s, _ = _login("student")
    r = s.post(f"{API}/announcements", json={"title": "no", "body": "no"})
    assert r.status_code == 403

def test_professor_can_post_announcement():
    s, _ = _login("prof")
    r = s.post(f"{API}/announcements", json={"title": "TEST prof ann", "body": "b"})
    assert r.status_code == 200


# ---------- Attendance ----------
def test_attendance_add_and_mark():
    s, _ = _login("student")
    code = f"T{uuid.uuid4().hex[:4].upper()}"
    r = s.post(f"{API}/attendance", json={"code": code, "name": "TEST Subject"})
    assert r.status_code == 200
    sid = r.json()["id"]
    assert r.json()["code"] == code.upper()
    r2 = s.post(f"{API}/attendance/{sid}/mark", json={"present": True})
    assert r2.status_code == 200
    r3 = s.post(f"{API}/attendance/{sid}/mark", json={"present": False})
    assert r3.status_code == 200
    lst = s.get(f"{API}/attendance").json()
    row = next(x for x in lst if x["id"] == sid)
    assert row["total"] == 2 and row["attended"] == 1


# ---------- Queries ----------
def test_query_create_encrypted_id_and_stage_peers():
    s, _ = _login("student")
    r = s.post(f"{API}/queries", json={
        "department": "Computer Science", "topic": "DBMS", "query": "TEST q?"
    })
    assert r.status_code == 200
    q = r.json()
    assert q["author_encrypted_id"].startswith("enc_usr_")
    assert q["stage"] == "peers"
    return q["id"]

def test_answer_and_resolve_query_by_author():
    s, _ = _login("student")
    qid = s.post(f"{API}/queries", json={
        "department": "CS", "topic": "T", "query": "TEST author resolve?"
    }).json()["id"]
    # Answer by someone else
    s2, _ = _login("senior")
    a = s2.post(f"{API}/queries/{qid}/answer", json={"text": "here you go"})
    assert a.status_code == 200
    # Non-author (senior) cannot resolve
    bad = s2.post(f"{API}/queries/{qid}/resolve")
    assert bad.status_code == 403
    # Author can resolve
    ok = s.post(f"{API}/queries/{qid}/resolve")
    assert ok.status_code == 200
    # GET reflects Resolved
    lst = s.get(f"{API}/queries").json()
    qq = next((x for x in lst if x["id"] == qid), None)
    if qq is None:
        # Might have been filtered? Only Archived are filtered out; Resolved should still be here
        assert False, "Resolved query missing from active list"
    assert qq["status"] == "Resolved"

def test_professor_can_resolve_any_query():
    s, _ = _login("student")
    qid = s.post(f"{API}/queries", json={"department": "CS", "query": "TEST prof resolve"}).json()["id"]
    sp, _ = _login("prof")
    r = sp.post(f"{API}/queries/{qid}/resolve")
    assert r.status_code == 200

def test_queries_archived_filter():
    s, _ = _login("student")
    r = s.get(f"{API}/queries", params={"archived": "true"})
    assert r.status_code == 200
    assert isinstance(r.json(), list)


# ---------- Clubs ----------
def test_clubs_are_manually_created():
    admin, _ = _login("admin")
    student, _ = _login("student")
    name = f"TEST Club {uuid.uuid4().hex[:6]}"
    # students cannot create clubs
    assert student.post(f"{API}/clubs", json={"name": name}).status_code == 403
    r = admin.post(f"{API}/clubs", json={"name": name, "category": "Tech", "description": "d",
                                          "cells": ["Media", "Design"], "archives": [{"year": 2025, "events": 3}]})
    assert r.status_code == 200
    club = r.json()
    assert club["cells"] == ["Design", "Media"] and club["archives"] == [{"year": 2025, "events": 3}]
    assert admin.post(f"{API}/clubs", json={"name": name}).status_code == 400          # duplicate name
    assert admin.post(f"{API}/clubs/{club['id']}/cells", json={"name": "Events"}).json()["cells"].count("Events") == 1
    assert admin.post(f"{API}/clubs/{club['id']}/archives", json={"year": 2024, "events": 5}).status_code == 200
    assert any(c["id"] == club["id"] for c in student.get(f"{API}/clubs").json())
    assert admin.delete(f"{API}/clubs/{club['id']}").status_code == 200


# ---------- Temp groups ----------
def test_temp_group_create_and_join():
    s, u = _login("student")
    r = s.post(f"{API}/temp-groups", json={"name": f"TEST Grp {uuid.uuid4().hex[:5]}", "hours": 6})
    assert r.status_code == 200
    gid = r.json()["id"]
    # Second user joins
    s2, u2 = _login("senior")
    r2 = s2.post(f"{API}/temp-groups/{gid}/join")
    assert r2.status_code == 200
    lst = s.get(f"{API}/temp-groups").json()
    g = next(x for x in lst if x["id"] == gid)
    assert u2["user_id"] in g["members"]


# ---------- Complaints ----------
def test_complaint_flow_student_admin():
    s, _ = _login("student")
    subj = f"TEST Complaint {uuid.uuid4().hex[:5]}"
    r = s.post(f"{API}/complaints", json={"subject": subj, "body": "issue"})
    assert r.status_code == 200
    cid = r.json()["id"]
    # student sees only own
    mine = s.get(f"{API}/complaints").json()
    assert any(x["id"] == cid for x in mine)
    # admin sees & responds
    sa, _ = _login("admin")
    all_c = sa.get(f"{API}/complaints").json()
    assert any(x["id"] == cid for x in all_c)
    resp = sa.post(f"{API}/complaints/{cid}/respond", json={"response": "will look into it"})
    assert resp.status_code == 200
    # verify persisted response
    all_c2 = sa.get(f"{API}/complaints").json()
    target = next(x for x in all_c2 if x["id"] == cid)
    assert target["response"] == "will look into it"
    assert target["status"] == "Responded"

def test_student_cannot_respond_to_complaint():
    s, _ = _login("student")
    cid = s.post(f"{API}/complaints", json={"subject": "TEST s", "body": "b"}).json()["id"]
    r = s.post(f"{API}/complaints/{cid}/respond", json={"response": "no"})
    assert r.status_code == 403


# ---------- Admin ----------
def test_admin_can_list_users_and_change_role():
    sa, admin = _login("admin")
    users = sa.get(f"{API}/admin/users").json()
    assert isinstance(users, list) and len(users) >= 7
    # find dcr
    dcr = next(u for u in users if u["email"] == "dcr@campus.edu")
    original = dcr["role"]
    new_role = "Senior" if original != "Senior" else "DCR"
    r = sa.post(f"{API}/admin/users/{dcr['user_id']}/role", json={"role": new_role})
    assert r.status_code == 200
    assert r.json()["user"]["role"] == new_role
    # verify persistence
    users2 = sa.get(f"{API}/admin/users").json()
    dcr2 = next(u for u in users2 if u["email"] == "dcr@campus.edu")
    assert dcr2["role"] == new_role
    # restore
    sa.post(f"{API}/admin/users/{dcr['user_id']}/role", json={"role": original})

def test_non_admin_cannot_list_users():
    s, _ = _login("student")
    r = s.get(f"{API}/admin/users")
    assert r.status_code == 403

def test_admin_invalid_role_rejected():
    sa, _ = _login("admin")
    users = sa.get(f"{API}/admin/users").json()
    target = users[0]
    r = sa.post(f"{API}/admin/users/{target['user_id']}/role", json={"role": "Overlord"})
    assert r.status_code == 400


# ---------- Stats ----------
def test_stats_overview_shape():
    s, _ = _login("cr")
    r = s.get(f"{API}/stats/overview")
    assert r.status_code == 200
    d = r.json()
    for k in ("announcements", "open_queries", "escalated_alumni", "clubs",
              "recent_announcements", "recent_queries"):
        assert k in d
    assert isinstance(d["announcements"], int)
    assert isinstance(d["recent_announcements"], list)
    assert isinstance(d["recent_queries"], list)
    assert isinstance(d["clubs"], int)
