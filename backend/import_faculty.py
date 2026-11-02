"""Import SVNIT_Faculty_Directory_Departmentwise.xlsx (240 faculty, office extensions, HODs) through your backend.

    pip install openpyxl
    python import_faculty.py "C:\\path\\SVNIT_Faculty_Directory_Departmentwise.xlsx" --dry-run
    python import_faculty.py "C:\\path\\SVNIT_Faculty_Directory_Departmentwise.xlsx" --upload https://<backend>.onrender.com --email ADMIN --password PASS [--create-accounts]

Also links each club's faculty coordinators to their directory entry (by name, only when unambiguous). Safe to repeat.
"""
import argparse
import http.cookiejar
import json
import sys
import time
import urllib.error
import urllib.request

from importer.faculty_sheet import parse_faculty


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("xlsx")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--upload", metavar="URL")
    ap.add_argument("--email")
    ap.add_argument("--password")
    ap.add_argument("--create-accounts", action="store_true",
                    help="also create one placeholder account per faculty member (Heads of Department become department administrators)")
    a = ap.parse_args()
    items = parse_faculty(a.xlsx)
    print(f"{len(items)} faculty, {sum(1 for f in items if f['is_hod'])} heads of department, "
          f"{sum(1 for f in items if f['extension'])} with an office extension")
    if a.dry_run or not a.upload:
        if not a.upload:
            print("(nothing sent — add --upload URL --email … --password …)")
        return
    if not (a.email and a.password):
        sys.exit("--upload needs --email and --password of an Administrator")
    base = a.upload.rstrip("/")
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))

    def post(path, body, tries=4):
        req = urllib.request.Request(base + path, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
        for n in range(1, tries + 1):
            try:
                with opener.open(req, timeout=240) as r:
                    return json.loads(r.read().decode())
            except urllib.error.HTTPError as e:
                if e.code < 500 or n == tries:
                    sys.exit(f"server said {e.code}: {e.read().decode()[:400]}")
            except Exception as e:                                   # noqa: BLE001
                if n == tries:
                    sys.exit(f"could not reach {base}: {e}")
            print("   retrying …")
            time.sleep(5 * n)

    post("/api/auth/login", {"email": a.email, "password": a.password})
    total = {}
    for i in range(0, len(items), 100):
        res = post("/api/admin/import-faculty", {"faculty": items[i:i + 100]})["stats"]
        total.update({k: total.get(k, 0) + v for k, v in res.items() if k.startswith("faculty_")})
        total.update({k: v for k, v in res.items() if not k.startswith("faculty_")})     # linking totals are absolute
        print(f"sent {min(i + 100, len(items))}/{len(items)}")
    print("done:", total)
    if a.create_accounts:
        res = post("/api/admin/faculty/create-accounts", {})["stats"]
        print("accounts:", res, "\n-> now open Academic Setup > Student placement > 'Staff to activate' and attach each person's real email.")


if __name__ == "__main__":
    main()
