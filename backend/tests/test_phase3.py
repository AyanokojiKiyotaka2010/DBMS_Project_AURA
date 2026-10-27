"""AURA Phase-3 additive feature tests: attachments, escalation notifications, professor analytics."""
import os
import uuid
import pytest
import requests

BASE = os.environ.get("REACT_APP_BACKEND_URL")
if not BASE:
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                BASE = line.split("=", 1)[1].strip()
BASE = BASE.rstrip("/")
API = f"{BASE}/api"

TINY_PNG_B64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4nGNgYGD4DwABBAEAwS2OUAAAAABJRU5ErkJggg=="

CREDS = {
    "admin": ("admin@campus.edu", "admin123"),
    "cr": ("cr@campus.edu", "cr12345"),
    "prof": ("prof@campus.edu", "prof12345"),
    "senior": ("senior@campus.edu", "senior12345"),
    "alumni": ("alumni@campus.edu", "alumni12345"),
    "student": ("student@campus.edu", "student123"),
    "dcr": ("dcr@campus.edu", "dcr12345"),
}


def _login(persona):
    email, pw = CREDS[persona]
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": email, "password": pw})
    assert r.status_code == 200, f"login {persona}: {r.status_code} {r.text}"
    return s


# ---------- Query attachments ----------
def test_query_create_with_attachments():
    s = _login("student")
    payload = {
        "department": "Computer Science",
        "topic": "TEST-att",
        "query": "TEST query with attachment",
        "attachments": [
            {"name": "pixel.png", "mime": "image/png", "data": TINY_PNG_B64},
        ],
    }
    r = s.post(f"{API}/queries", json=payload)
    assert r.status_code == 200, r.text
    q = r.json()
    assert isinstance(q.get("attachments"), list) and len(q["attachments"]) == 1
    a = q["attachments"][0]
    assert a["name"] == "pixel.png"
    assert a["mime"] == "image/png"
    assert a["data"] == TINY_PNG_B64
    assert isinstance(a["size"], int) and a["size"] > 0


def test_query_attachments_persist_in_list():
    s = _login("student")
    marker = f"TEST-persist-{uuid.uuid4().hex[:6]}"
    r = s.post(f"{API}/queries", json={
        "department": "CS", "topic": "P", "query": marker,
        "attachments": [{"name": "p.png", "mime": "image/png", "data": TINY_PNG_B64}],
    })
    qid = r.json()["id"]
    lst = s.get(f"{API}/queries").json()
    found = next(x for x in lst if x["id"] == qid)
    assert len(found["attachments"]) == 1
    assert found["attachments"][0]["data"] == TINY_PNG_B64


def test_query_rejects_more_than_3_attachments():
    s = _login("student")
    atts = [{"name": f"f{i}.png", "mime": "image/png", "data": TINY_PNG_B64} for i in range(4)]
    r = s.post(f"{API}/queries", json={
        "department": "CS", "topic": "T", "query": "TEST too many", "attachments": atts,
    })
    assert r.status_code == 400


def test_query_rejects_oversize_attachment():
    s = _login("student")
    # ~3 MB of base64 -> ~2.25MB decoded -> exceeds 2MB
    big = "A" * (3 * 1024 * 1024)
    r = s.post(f"{API}/queries", json={
        "department": "CS", "topic": "T", "query": "TEST oversize",
        "attachments": [{"name": "big.bin", "mime": "application/octet-stream", "data": big}],
    })
    assert r.status_code == 400


# ---------- Complaint attachments ----------
def test_complaint_create_with_attachments():
    s = _login("student")
    r = s.post(f"{API}/complaints", json={
        "subject": f"TEST cmp {uuid.uuid4().hex[:5]}",
        "body": "with file",
        "attachments": [{"name": "p.png", "mime": "image/png", "data": TINY_PNG_B64}],
    })
    assert r.status_code == 200
    c = r.json()
    assert len(c["attachments"]) == 1
    assert c["attachments"][0]["mime"] == "image/png"
    assert c["attachments"][0]["size"] > 0


def test_complaint_rejects_oversize():
    s = _login("student")
    big = "A" * (3 * 1024 * 1024)
    r = s.post(f"{API}/complaints", json={
        "subject": "TEST big", "body": "b",
        "attachments": [{"name": "big.bin", "mime": "application/octet-stream", "data": big}],
    })
    assert r.status_code == 400


def test_complaint_rejects_more_than_3():
    s = _login("student")
    atts = [{"name": f"f{i}.png", "mime": "image/png", "data": TINY_PNG_B64} for i in range(4)]
    r = s.post(f"{API}/complaints", json={
        "subject": "TEST many", "body": "b", "attachments": atts,
    })
    assert r.status_code == 400


# ---------- Escalation notifications ----------
def test_escalations_tier_senior():
    s = _login("senior")
    r = s.get(f"{API}/notifications/escalations")
    assert r.status_code == 200
    d = r.json()
    assert d["tier"] == "seniors"
    assert "count" in d and "items" in d
    assert isinstance(d["items"], list)
    assert d["count"] == len(d["items"])


def test_escalations_tier_alumni():
    s = _login("alumni")
    d = s.get(f"{API}/notifications/escalations").json()
    assert d["tier"] == "alumni"


def test_escalations_tier_professor_any():
    s = _login("prof")
    d = s.get(f"{API}/notifications/escalations").json()
    assert d["tier"] == "any"


def test_escalations_tier_admin_any():
    s = _login("admin")
    d = s.get(f"{API}/notifications/escalations").json()
    assert d["tier"] == "any"


def test_escalations_student_empty():
    s = _login("student")
    d = s.get(f"{API}/notifications/escalations").json()
    assert d["tier"] is None
    assert d["count"] == 0
    assert d["items"] == []


def test_escalations_cr_empty():
    s = _login("cr")
    d = s.get(f"{API}/notifications/escalations").json()
    assert d["tier"] is None
    assert d["count"] == 0


def test_escalations_dcr_empty():
    s = _login("dcr")
    d = s.get(f"{API}/notifications/escalations").json()
    assert d["tier"] is None


# ---------- Professor analytics ----------
def test_professor_analytics_structure():
    s = _login("student")  # visible to all
    r = s.get(f"{API}/analytics/professors")
    assert r.status_code == 200
    d = r.json()
    assert "professors" in d and isinstance(d["professors"], list)
    assert "unanswered_topics" in d and isinstance(d["unanswered_topics"], list)
    assert "totals" in d
    for k in ("professor_answers", "open_queries", "unanswered_48h"):
        assert k in d["totals"], f"missing totals.{k}"
    # unanswered items shape
    for u in d["unanswered_topics"]:
        assert "topic" in u and "count" in u
    # each professor row shape
    for p in d["professors"]:
        for k in ("name", "answers", "avg_response_hours", "fastest_response_hours", "topics", "resolved_queries"):
            assert k in p, f"missing prof.{k}"


def test_professor_analytics_reflects_new_prof_answer():
    """Create a query, professor answers it, verify analytics counts the answer."""
    ss = _login("student")
    qid = ss.post(f"{API}/queries", json={
        "department": "CS", "topic": "TEST-analytics", "query": "TEST for analytics"
    }).json()["id"]
    sp = _login("prof")
    a = sp.post(f"{API}/queries/{qid}/answer", json={"text": "TEST prof answer"})
    assert a.status_code == 200
    # Now fetch analytics
    d = ss.get(f"{API}/analytics/professors").json()
    prof_names = [p["name"] for p in d["professors"]]
    assert "Prof. Alan Turing" in prof_names, f"expected Prof. Alan Turing in {prof_names}"
    row = next(p for p in d["professors"] if p["name"] == "Prof. Alan Turing")
    assert row["answers"] >= 1
    assert d["totals"]["professor_answers"] >= 1
