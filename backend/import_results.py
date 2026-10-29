"""Import SVNIT 'result sheet' PDFs (folders 1st_year … 4th_year) into AURA.

    python import_results.py C:\\path\\to\\btech              # years shift up by one, 4th-year cohort -> Alumni
    python import_results.py C:\\path\\to\\btech --dry-run    # parse + validate only, touch nothing
    python import_results.py C:\\path\\to\\btech --graduates skip

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


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("folder")
    ap.add_argument("--graduates", choices=["alumni", "skip"], default="alumni")
    ap.add_argument("--dry-run", action="store_true")
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

    import db
    from importer.loader import load
    await db.init_pool()
    await db.ensure_schema()
    await load(parsed, graduates=a.graduates)
    await db.close_pool()


if __name__ == "__main__":
    asyncio.run(main())
