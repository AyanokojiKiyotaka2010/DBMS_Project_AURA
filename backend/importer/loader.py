"""Load parsed result sheets into the AURA database (works on MySQL via db.py; tests use sqlite).

Rules
  * Folder 1st_year .. 4th_year = the year the cohort was in when the sheet was issued.
    Students are now one year higher: 1st->2nd, 2nd->3rd, 3rd->4th; the 4th-year cohort has
    graduated -> role Alumni (or skipped with graduates='skip').
  * Courses keep the year / semester they were taken in (a Sem-2 course is a 1st-year course).
  * Honors / Minor sheets are skipped (they would mix extra courses into the regular CGPA).
  * Imported students get a placeholder e-mail (<admission-no>@import.invalid) and an unusable
    password, so they cannot log in until the college decides how accounts are claimed.
  * Re-running is safe: users (by roll no), courses, enrolments, results are only added once.
"""
import re

import db
from common_time import now_db
from .result_sheets import GRADE_POINTS, SEM_NO

ORD = {1: "1st Year", 2: "2nd Year", 3: "3rd Year", 4: "4th Year"}
CHUNK = 1000


def dept_name(branch: str) -> str:
    b = re.sub(r"\s+", " ", branch.replace("( ", "(")).strip()
    if "INTEGRATED" in b.upper():
        return "Integrated B.Tech + M.Tech (AI)"
    return re.sub(r"\bAnd\b", "and", b.title())


def _chunks(seq, n=CHUNK):
    for i in range(0, len(seq), n):
        yield seq[i:i + n]


def _in(n):
    return ",".join(["%s"] * n)


async def load(sheets, graduates="alumni", log=print):
    """sheets: list of (folder_year:int, parsed_sheet:dict). Returns a stats dict."""
    stats = {"sheets": 0, "skipped_sheets": 0, "users_new": 0, "users_existing": 0, "courses_new": 0,
             "enrollments_new": 0, "results_new": 0, "semester_rows_new": 0, "alumni": 0, "skipped_graduates": 0}
    now = now_db()

    # ---- structure: years
    year_id = {}
    for lvl, label in ORD.items():
        r = await db.one("SELECT id FROM academic_years WHERE level_no=%s", (lvl,))
        year_id[lvl] = r["id"] if r else await db.run("INSERT INTO academic_years (label, level_no) VALUES (%s,%s)", (label, lvl))

    dept_cache, div_cache, course_cache = {}, {}, {}

    async def dept(name):
        if name not in dept_cache:
            r = await db.one("SELECT id FROM departments WHERE name=%s", (name,))
            dept_cache[name] = r["id"] if r else await db.run("INSERT INTO departments (name) VALUES (%s)", (name,))
        return dept_cache[name]

    async def division(d_id, y_id):
        k = (d_id, y_id)
        if k not in div_cache:
            r = await db.one("SELECT id FROM divisions WHERE department_id=%s AND year_id=%s AND name='A'", k)
            div_cache[k] = r["id"] if r else await db.run(
                "INSERT INTO divisions (department_id, year_id, name) VALUES (%s,%s,'A')", k)
        return div_cache[k]

    existing_users = {r["roll_no"]: r["id"] for r in await db.all("SELECT id, roll_no FROM users WHERE roll_no IS NOT NULL")}
    user_of = {}                                   # roll_no -> user id (new or existing)
    to_enrol = []                                  # (roll_no, course_id, letter)
    sem_rows = []                                  # (roll_no, semester, sgpa, cgpa, reg, earned)

    for folder_year, sh in sheets:
        if sh["kind"] != "regular" or not sh["students"]:
            stats["skipped_sheets"] += 1
            continue
        stats["sheets"] += 1
        d_id = await dept(dept_name(sh["branch"]))
        course_sem = SEM_NO.get(sh["semester_name"].upper(), folder_year * 2)
        graduated = folder_year >= 4
        now_year = None if graduated else year_id[folder_year + 1]

        # courses of this sheet
        cid = {}
        for code, credit in sh["courses"].items():
            k = (code, d_id)
            if k not in course_cache:
                r = await db.one("SELECT id FROM courses WHERE code=%s AND department_id=%s", k)
                if r:
                    course_cache[k] = r["id"]
                else:
                    base = sh["course_names"].get(code) or code
                    name = (base + " (Practical)") if code.endswith(" P") else base
                    course_cache[k] = await db.run(
                        "INSERT INTO courses (code,name,credits,max_marks,department_id,year_id,semester) VALUES (%s,%s,%s,100,%s,%s,%s)",
                        (code, name[:160], credit, d_id, year_id[folder_year], course_sem))
                    stats["courses_new"] += 1
            cid[code] = course_cache[k]

        for st in sh["students"]:
            roll = st["admission_no"]
            if graduated and graduates == "skip":
                stats["skipped_graduates"] += 1
                continue
            if roll not in user_of:
                if roll in existing_users:
                    user_of[roll] = existing_users[roll]
                    stats["users_existing"] += 1
                else:
                    role = "Alumni" if graduated else "Student"
                    div = None if graduated else await division(d_id, now_year)
                    user_of[roll] = await db.run(
                        "INSERT INTO users (name,email,password_hash,role,department_id,year_id,division_id,roll_no,created_at) "
                        "VALUES (%s,%s,'!imported',%s,%s,%s,%s,%s,%s)",
                        (st["name"].title()[:120], f"{roll.lower()}@import.invalid", role, d_id, now_year, div, roll, now))
                    stats["users_new"] += 1
                    stats["alumni"] += 1 if graduated else 0
            for code, letter in st["grades"].items():
                to_enrol.append((roll, cid[code], letter))
            sem_rows.append((roll, st["semester"], st["sgpa"], st["cgpa"], st["reg_credit"], st["earned_credit"]))

    # ---- enrolments (skip pairs that already exist)
    course_ids = sorted({c for _, c, _ in to_enrol})
    have = set()
    for part in _chunks(course_ids, 200):
        for r in await db.all(f"SELECT student_id, course_id FROM enrollments WHERE course_id IN ({_in(len(part))})", tuple(part)):
            have.add((r["student_id"], r["course_id"]))
    new_pairs = []
    for roll, c, _ in to_enrol:
        key = (user_of[roll], c)
        if key not in have:
            have.add(key)
            new_pairs.append(key)
    for part in _chunks(new_pairs):
        await db.many("INSERT INTO enrollments (student_id, course_id) VALUES (%s,%s)", part)
    stats["enrollments_new"] = len(new_pairs)

    # ---- results (one per enrolment, only where none exists)
    enr = {}
    for part in _chunks(course_ids, 200):
        for r in await db.all(f"SELECT id, student_id, course_id FROM enrollments WHERE course_id IN ({_in(len(part))})", tuple(part)):
            enr[(r["student_id"], r["course_id"])] = r["id"]
    done = set()
    for part in _chunks(sorted(enr.values()), 2000):
        for r in await db.all(f"SELECT enrollment_id FROM results WHERE enrollment_id IN ({_in(len(part))})", tuple(part)):
            done.add(r["enrollment_id"])
    rows = []
    for roll, c, letter in to_enrol:
        eid = enr[(user_of[roll], c)]
        if eid in done:
            continue
        done.add(eid)
        gp = GRADE_POINTS.get(letter, 0)
        rows.append((eid, gp, letter, "PASS" if gp > 0 else "FAIL", now))
    for part in _chunks(rows):
        await db.many("INSERT INTO results (enrollment_id,marks_obtained,percentage,grade_point,grade_letter,status,updated_at) "
                      "VALUES (%s,NULL,NULL,%s,%s,%s,%s)", part)
    stats["results_new"] = len(rows)

    # ---- official SGPA / CGPA per semester
    have_sem = {(r["student_id"], r["semester"]) for r in await db.all("SELECT student_id, semester FROM semester_results")}
    new_sem = []
    for roll, sem, sgpa, cgpa, reg, earned in sem_rows:
        key = (user_of[roll], sem)
        if key not in have_sem:
            have_sem.add(key)
            new_sem.append((key[0], sem, sgpa, cgpa, reg, earned))
    for part in _chunks(new_sem):
        await db.many("INSERT INTO semester_results (student_id,semester,sgpa,cgpa,registered_credits,earned_credits) "
                      "VALUES (%s,%s,%s,%s,%s,%s)", part)
    stats["semester_rows_new"] = len(new_sem)
    log(f"import done: {stats}")
    return stats
