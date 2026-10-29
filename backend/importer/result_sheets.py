"""Parser for SVNIT 'REPORT SHEET SHOWING RESULT OF CANDIDATES' PDFs (needs `pdftotext` from poppler).

parse_pdf(path) -> {
    'title': str, 'program': 'B.TECH. I', 'semester_name': 'SECOND', 'branch': 'COMPUTER SCIENCE AND ENGINEERING',
    'kind': 'regular' | 'honors' | 'minor', 'courses': [...], 'students': [...]
}
Each student: admission_no, name, semester, grades{course_code: letter}, credits{course_code: credit},
              reg_credit, earned_credit, sgpa, cgpa, backlog_credits.
"""
import re
import subprocess

GRADE_POINTS = {"AA": 10, "AB": 9, "BB": 8, "BC": 7, "CC": 6, "CD": 5, "DD": 4, "FF": 0}
NOT_PASSED = {"FF", "II", "NA", "XX"}           # FF fail, II incomplete, NA not appeared, XX unsatisfactory attendance
GRADE_RE = re.compile(r"\b(AA|AB|BB|BC|CC|CD|DD|FF|II|NA|XX)\b")
CODE_RE = re.compile(r"\b[A-Z]{2,6}\d{2,3}(?: [TP])?\b")
ADM_RE = re.compile(r"^\s*([UI]\d{2}[A-Z]{2}\d{3})\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)")
STU_RE = re.compile(r"^\s*Semester\s*:\s*(\d+)\s+(.+?)(?:\s{3,}BACKLOG\s*:)?\s*$")
TITLE_RE = re.compile(r"RESULT OF CANDIDATES APPEARED AT (.*?)\s+(FIRST|SECOND|THIRD|FOURTH|FIFTH|SIXTH|SEVENTH|EIGHT|EIGHTH)\s+SEMESTER\s*(.*?)\s+AT REGULAR", re.S)
INTEGRATED_RE = re.compile(r"INTEGRATED", re.I)
SEM_NO = {"FIRST": 1, "SECOND": 2, "THIRD": 3, "FOURTH": 4, "FIFTH": 5, "SIXTH": 6, "SEVENTH": 7, "EIGHT": 8, "EIGHTH": 8}
_SMALL = {"AND", "OF", "FOR", "IN", "THE", "TO", "&", "(PRAC.)"}


def _text(path):
    return subprocess.run(["pdftotext", "-layout", path, "-"], capture_output=True, text=True, check=True).stdout


def _centers(line, regex):
    return [((m.start() + m.end()) / 2.0, m.group(0)) for m in regex.finditer(line)]


def _nearest(centers, x):
    return min(centers, key=lambda c: abs(c[0] - x))


def _join_name(parts):
    """Header descriptions wrap mid-word ('PROGRAMMI' + 'NG'); glue a cut word back together."""
    words = " ".join(parts).split()
    out = []
    for w in words:
        if out and len(out[-1]) >= 8 and out[-1].isalpha() and w.isalpha() and w not in _SMALL and len(w) <= 5:
            out[-1] += w
        else:
            out.append(w)
    name = " ".join(out)
    return re.sub(r"\s*\(PRAC\.\)", "", name).strip().title()


def parse_pdf(path):
    text = _text(path)
    flat = " ".join(text.split("\n")[:8])
    m = TITLE_RE.search(re.sub(r"\s+", " ", flat))
    title = m.group(0) if m else ""
    program, sem_name, branch = (m.group(1), m.group(2), m.group(3)) if m else ("", "", "")
    if m and not branch.strip():
        branch = "INTEGRATED B.TECH + M.TECH (AI)" if INTEGRATED_RE.search(program) else program
    kind = "honors" if "HONORS" in branch.upper() else "minor" if "MINOR" in branch.upper() else "regular"

    lines = text.split("\n")
    hdr_codes, hdr_credits = [], {}
    courses, students, names = {}, [], {}
    i = 0
    while i < len(lines):
        ln = lines[i]
        if "Course Code" in ln:
            hdr_codes = _centers(ln.split("Course Code", 1)[1].rjust(len(ln)), CODE_RE)
            hdr_codes = [(c, code) for c, code in hdr_codes]
            # credit row = next non-empty line starting with 'Credit'
            j = i + 1
            while j < len(lines) and "Credit" not in lines[j][:70]:
                j += 1
            nums = _centers(lines[j], re.compile(r"\b\d+\.\d{2}\b"))
            hdr_credits = {}
            for c, code in hdr_codes:
                x, val = _nearest(nums, c) if nums else (0, "0")
                hdr_credits[code] = float(val)
                courses[code] = float(val)
            # wrapped description lines sit between the credit row and the first student
            desc, d = {}, j + 1
            first_x = hdr_codes[0][0] - 9 if hdr_codes else 0
            while d < len(lines) and not STU_RE.match(lines[d]):
                for pm in re.finditer(r"\S+", lines[d]):
                    cx = (pm.start() + pm.end()) / 2.0
                    if pm.start() < first_x or not hdr_codes:
                        continue
                    _, code = _nearest(hdr_codes, cx)
                    desc.setdefault(code, []).append(pm.group(0))
                d += 1
            for code, parts in desc.items():
                names[code] = _join_name(parts)
            i = j
        sm = STU_RE.match(ln)
        if sm and hdr_codes:
            sem_no, name = int(sm.group(1)), re.sub(r"\s+", " ", sm.group(2)).strip()
            name = re.sub(r"\s*BACKLOG\s*:.*$", "", name).strip()
            grade_line, adm_line, backlog_cr = "", "", 0.0
            k = i + 1
            while k < len(lines) and k < i + 6:
                if ADM_RE.match(lines[k]):
                    adm_line = lines[k]
                    break
                if GRADE_RE.search(lines[k]) and not grade_line:
                    grade_line = lines[k]
                k += 1
            am = ADM_RE.match(adm_line) if adm_line else None
            if am:
                grades = {}
                for x, g in _centers(grade_line, GRADE_RE):
                    c, code = _nearest(hdr_codes, x)
                    grades[code] = g
                # backlog credits sits at the far right of the grade line(s)
                for ln2 in lines[i:k + 1]:
                    bm = re.search(r"BACKLOG\s*:\s*$", ln2)
                    if bm:
                        right = re.search(r"\s(\d+)\s*$", grade_line)
                        if right:
                            backlog_cr = float(right.group(1))
                            # that trailing number is not a grade; make sure it is not counted
                students.append({
                    "admission_no": am.group(1), "name": name, "semester": sem_no,
                    "grades": grades, "credits": dict(hdr_credits),
                    "reg_credit": float(am.group(2)), "earned_credit": float(am.group(3)),
                    "sgpa": float(am.group(4)), "cgpa": float(am.group(5)), "backlog_credits": backlog_cr,
                })
                i = k
        i += 1
    return {"title": title, "program": program, "semester_name": sem_name, "branch": branch, "kind": kind,
            "courses": courses, "course_names": names, "students": students}


def recompute_sgpa(st):
    """SGPA from letter grades: sum(credit*gp)/sum(credit) over the courses the student has a grade for."""
    num = den = 0.0
    for code, g in st["grades"].items():
        cr = st["credits"].get(code, 0)
        num += cr * GRADE_POINTS.get(g, 0)
        den += cr
    return round(num / den, 2) if den else 0.0
