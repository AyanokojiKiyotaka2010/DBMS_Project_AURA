"""Read SVNIT_Faculty_Directory_Departmentwise.xlsx ('All Faculty' sheet) -> list of dicts (needs openpyxl)."""
import re


def _c(v):
    return re.sub(r"\s+", " ", str(v)).strip() if v is not None else ""


def parse_faculty(path):
    import openpyxl
    wb = openpyxl.load_workbook(path, data_only=True)
    out = []
    for r in wb["All Faculty"].iter_rows(min_row=1, values_only=True):
        if not r[0] or not r[1] or _c(r[0]) in ("Department",) or str(r[0]).startswith("SVNIT Faculty") or str(r[0]).startswith("240 "):
            continue
        out.append({"department": _c(r[0])[:160], "name": _c(r[1])[:160], "extension": _c(r[2])[:60],
                    "is_hod": _c(r[3]).lower() in ("yes", "y", "true", "1"), "affiliation": _c(r[4])[:300],
                    "note": _c(r[5])[:300], "source_url": _c(r[6]).split(" ")[0][:500]})
    return out
