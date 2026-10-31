"""Import SVNIT_Clubs_Chapters_Directory.xlsx (clubs, links, student leaders, faculty coordinators).

    pip install openpyxl
    python import_clubs.py "C:\\path\\SVNIT_Clubs_Chapters_Directory.xlsx" --dry-run
    python import_clubs.py "C:\\path\\SVNIT_Clubs_Chapters_Directory.xlsx" --upload https://<backend>.onrender.com --email ADMIN --password PASS

Safe to repeat: clubs are matched by name and updated, people are only added once.
"""
import argparse
import http.cookiejar
import json
import sys
import time
import urllib.error
import urllib.request

from importer.club_sheets import parse_clubs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("xlsx")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--upload", metavar="URL")
    ap.add_argument("--email")
    ap.add_argument("--password")
    a = ap.parse_args()

    clubs, unmatched = parse_clubs(a.xlsx)
    people = sum(len(c["people"]) for c in clubs)
    print(f"{len(clubs)} clubs, {people} people (student leaders, members, faculty coordinators)")
    if unmatched:
        print("WARNING - sheet labels that matched no club (skipped):", unmatched)
    for c in clubs:
        if c["people"]:
            print(f"  {c['name'][:60]:62} {len(c['people']):3} people")
    if a.dry_run or not a.upload:
        if not a.upload:
            print("\n(nothing sent — add --upload URL --email … --password … to import)")
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
    for i in range(0, len(clubs), 10):                       # 10 clubs per request
        res = post("/api/admin/import-clubs", {"clubs": clubs[i:i + 10]})["stats"]
        for k, v in res.items():
            total[k] = total.get(k, 0) + v
        print(f"sent {min(i + 10, len(clubs))}/{len(clubs)}")
    print("done:", total)


if __name__ == "__main__":
    main()
