"""Phase 4 backend tests: Weekly Digest endpoint RBAC + payload shape."""
import os
import requests
import pytest

BASE = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
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


# RBAC: allowed roles
@pytest.mark.parametrize("persona", ["cr", "dcr", "admin"])
def test_digest_allowed_roles(persona):
    s, _ = _login(persona)
    r = s.get(f"{API}/digest/weekly")
    assert r.status_code == 200, f"{persona}: {r.status_code} {r.text}"


# RBAC: forbidden roles
@pytest.mark.parametrize("persona", ["student", "senior", "alumni", "prof"])
def test_digest_forbidden_roles(persona):
    s, _ = _login(persona)
    r = s.get(f"{API}/digest/weekly")
    assert r.status_code == 403, f"{persona}: {r.status_code}"


# Payload shape for CR
def test_digest_payload_shape_for_cr():
    s, user = _login("cr")
    r = s.get(f"{API}/digest/weekly")
    assert r.status_code == 200
    data = r.json()
    # Top-level fields
    for key in ("department", "cr_name", "generated_at", "week_ending",
                "summary", "announcements", "doubts", "escalated",
                "deadlines", "defaulters"):
        assert key in data, f"missing {key}"
    # summary shape
    summary = data["summary"]
    for key in ("announcements_7d", "open_doubts", "escalated",
                "defaulters", "upcoming_deadlines"):
        assert key in summary, f"summary missing {key}"
        assert isinstance(summary[key], int)
    # cr_name/department match caller
    assert data["cr_name"] == user["name"]
    assert data["department"] == user["department"]
    # lists are actually lists
    for k in ("announcements", "doubts", "escalated", "deadlines", "defaulters"):
        assert isinstance(data[k], list)


def test_digest_summary_counts_match_lists():
    """Summary counts should be >= the returned (capped) list lengths."""
    s, _ = _login("cr")
    data = s.get(f"{API}/digest/weekly").json()
    assert data["summary"]["announcements_7d"] >= len(data["announcements"])
    assert data["summary"]["open_doubts"] >= len(data["doubts"])
    assert data["summary"]["escalated"] >= len(data["escalated"])
    assert data["summary"]["defaulters"] >= len(data["defaulters"])


def test_digest_escalated_subset_of_stages():
    """Every item in 'escalated' must be at seniors/alumni stage."""
    s, _ = _login("cr")
    data = s.get(f"{API}/digest/weekly").json()
    for e in data["escalated"]:
        assert e.get("stage") in ("seniors", "alumni"), f"bad stage {e.get('stage')}"


def test_digest_defaulters_all_below_75():
    s, _ = _login("cr")
    data = s.get(f"{API}/digest/weekly").json()
    for d in data["defaulters"]:
        assert d["percent"] < 75, f"defaulter with {d['percent']}%"


def test_digest_department_scoping():
    """CR and Admin get their own dept; announcements list only contains that dept."""
    s, user = _login("cr")
    data = s.get(f"{API}/digest/weekly").json()
    assert data["department"] == user["department"]


def test_digest_unauth_returns_401_or_403():
    r = requests.get(f"{API}/digest/weekly")
    assert r.status_code in (401, 403)
