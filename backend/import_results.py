"""Import SVNIT 'result sheet' PDFs (folders 1st_year … 4th_year) into AURA.

    python import_results.py C:\\path\\to\\btech              # years shift up by one, 4th-year cohort -> Alumni
    python import_results.py C:\\path\\to\\btech --dry-run    # parse + validate only, touch nothing
    python import_results.py C:\\path\\to\\btech --graduates skip
    python import_results.py C:\\path\\to\\btech --upload https://<backend>.onrender.com --email admin@x --password ...

Requires poppler's `pdftotext` on PATH (Windows: install poppler and add its bin folder to PATH).
The PDFs contain real students' data: keep them out of git (see .gitignore) and out of any public place.
"""
import argparse
import asyncio
import re
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()
from importer.result_sheets import parse_pdf, recompute_sgpa  # noqa: E402

YEAR_DIR = re.compile(r"^(\d)(?:st|nd|rd|th)_year$", re.I)


def collect(root: Path):
    sheets = []
    for d in sorted(root.rglob("*")):
        m = YEAR_DIR.match(d.name) if d.is_dir() else None
        if not m:
            continue
        for pdf in sorted(d.glob("*.pdf")):
            sheets.append((int(m.group(1)), pdf))
    return sheets


def upload(a, parsed):
    """Parse locally, POST each regular sheet to <URL>/api/admin/import-sheet (idempotent, retried)."""
    import http.cookiejar
    import json
    import time
    import urllib.error
    import urllib.request

    base = a.upload.rstrip("/")
    if not (a.email and a.password):
        sys.exit("--upload needs --email and --password of an Administrator")
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))

    def post(path, body, tries=4):
        req = urllib.request.Request(base + path, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
        for n in range(1, tries + 1):
            try:
                with opener.open(req, timeout=240) as r:
                    return json.loads(r.read().decode())
            except urllib.error.HTTPError as e:
                detail = e.read().decode()[:400]
                if e.code < 500 or n == tries:
                    sys.exit(f"server said {e.code}: {detail}")
            except Exception as e:                                   # network hiccup / Render cold start
                if n == tries:
                    sys.exit(f"could not reach {base}: {e}")
            print(f"   retrying ({n}/{tries - 1}) …")
            time.sleep(5 * n)

    print("logging in …")
    post("/api/auth/login", {"email": a.email, "password": a.password})
    todo = [(y, s) for y, s in parsed if s["kind"] == "regular" and s["students"]]
    total = {}
    for i, (year, sh) in enumerate(todo, 1):
        body = {"folder_year": year, "graduates": a.graduates, "sheet": {
            "kind": sh["kind"], "branch": sh["branch"], "semester_name": sh["semester_name"],
            "courses": sh["courses"], "course_names": sh["course_names"],
            "students": [{k: st[k] for k in ("admission_no", "name", "semester", "grades", "reg_credit",
                                              "earned_credit", "sgpa", "cgpa")} for st in sh["students"]]}}
        res = post("/api/admin/import-sheet", body)["stats"]
        for k, v in res.items():
            total[k] = total.get(k, 0) + v
        print(f"[{i}/{len(todo)}] year {year} {sh['branch'][:40]:42} students={len(sh['students']):4} "
              f"new users={res['users_new']:4} new grades={res['results_new']:5}")
    print("\nupload finished:", total)


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("folder")
    ap.add_argument("--graduates", choices=["alumni", "skip"], default="alumni")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--upload", metavar="URL", help="send the parsed data to a deployed backend (e.g. https://xyz.onrender.com) "
                    "instead of connecting to MySQL directly")
    ap.add_argument("--email", help="administrator e-mail (with --upload)")
    ap.add_argument("--password", help="administrator password (with --upload)")
    a = ap.parse_args()

    files = collect(Path(a.folder))
    if not files:
        sys.exit("No <n>th_year folders with PDFs found under " + a.folder)
    parsed, bad = [], 0
    for year, pdf in files:
        sh = parse_pdf(str(pdf))
        mism = [s for s in sh["students"] if abs(recompute_sgpa(s) - s["sgpa"]) > 0.011]
        bad += len(mism)
        print(f"{year}  {pdf.name[:52]:54} {sh['kind']:8} students={len(sh['students']):4} sgpa-mismatch={len(mism)}")
        parsed.append((year, sh))
    print(f"\n{sum(len(s['students']) for _, s in parsed)} student rows parsed; {bad} SGPA mismatches")
    if a.dry_run:
        return

    if a.upload:
        upload(a, parsed)
        return

    import db
    from importer.loader import load
    await db.init_pool()
    await db.ensure_schema()
    await load(parsed, graduates=a.graduates)
    await db.close_pool()


if __name__ == "__main__":
    asyncio.run(main())
