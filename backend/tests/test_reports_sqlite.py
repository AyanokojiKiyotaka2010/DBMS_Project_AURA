"""Report SQL tests on an in-memory sqlite DB (no server, no MySQL needed).

Run:  python3 tests/test_reports_sqlite.py      (or: pytest -n 0 tests/test_reports_sqlite.py)
"""
import asyncio
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, os.path.dirname(HERE)]

import db  # noqa: E402
import sqlite_db  # noqa: E402
import report_service as rs  # noqa: E402
from grading import grade_for  # noqa: E402

NOW = "2026-01-01 00:00:00"


def build():
    c = sqlite_db.install(db)
    c.run("INSERT INTO departments (name, code) VALUES ('Computer Science','CSE')")   # 1
    c.run("INSERT INTO departments (name, code) VALUES ('Mechanical','ME')")          # 2
    c.run("INSERT INTO academic_years (label, level_no) VALUES ('2nd Year', 2)")      # 1
    c.run("INSERT INTO academic_years (label, level_no) VALUES ('3rd Year', 3)")      # 2
    for dept, yr, name in [(1, 1, 'A'), (1, 1, 'B'), (1, 2, 'A'), (2, 1, 'A')]:       # div 1..4
        c.run("INSERT INTO divisions (department_id, year_id, name) VALUES (%s,%s,%s)", (dept, yr, name))

    def user(name, role, dept, yr, div, roll=None):
        return c.run(
            "INSERT INTO users (name,email,password_hash,role,department_id,year_id,division_id,roll_no,created_at) "
            "VALUES (%s,%s,'x',%s,%s,%s,%s,%s,%s)",
            (name, name.lower().replace(" ", "") + "@t.edu", role, dept, yr, div, roll, NOW))

    ids = {}
    ids["hod"] = user("Hod Cse", "Administrator", 1, None, None)
    ids["super"] = user("Super Admin", "Administrator", None, None, None)
    ids["prof"] = user("Prof Turing", "Professor", 1, None, None)
    ids["prof_me"] = user("Prof Me", "Professor", 2, None, None)
    ids["cr"] = user("Cara CR", "CR", 1, 1, 1, "CS001")           # division CSE/2nd/A
    ids["dcr"] = user("Dan DCR", "DCR", 1, 1, 2, "CS002")         # division CSE/2nd/B
    ids["s1"] = user("Asha", "Student", 1, 1, 1, "CS003")
    ids["s2"] = user("Bala", "Student", 1, 1, 1, "CS004")
    ids["s3"] = user("Chitra", "Student", 1, 1, 2, "CS005")
    ids["s4"] = user("Dev", "Student", 1, 2, 3, "CS006")
    ids["m1"] = user("Mech Kid", "Student", 2, 1, 4, "ME001")
    ids["senior"] = user("Old Senior", "Senior", 1, 2, None)

    # courses: (code, credits, dept, year, sem)
    cid = {}
    for code, cr, dept, yr, sem in [("CS201", 4, 1, 1, 3), ("CS202", 2, 1, 1, 3), ("CS203", 3, 1, 1, 4),
                                    ("CS301", 4, 1, 2, 5), ("ME201", 3, 2, 1, 3)]:
        cid[code] = c.run("INSERT INTO courses (code,name,credits,max_marks,department_id,year_id,semester,professor_id) "
                          "VALUES (%s,%s,%s,100,%s,%s,%s,%s)",
                          (code, code + " name", cr, dept, yr, sem, ids["prof"] if dept == 1 else ids["prof_me"]))

    def enroll(student, code, marks=None):
        eid = c.run("INSERT INTO enrollments (student_id, course_id) VALUES (%s,%s)", (ids[student], cid[code]))
        if marks is not None:
            g = grade_for(marks, 100)
            c.run("INSERT INTO results (enrollment_id,marks_obtained,percentage,grade_point,grade_letter,status,updated_at) "
                  "VALUES (%s,%s,%s,%s,%s,%s,%s)",
                  (eid, marks, g["percentage"], g["grade_point"], g["grade_letter"], g["status"], NOW))
        return eid

    # Asha: CS201(4cr,92->10) CS202(2cr,75->8)  CS203(3cr,85->9, sem4)
    enroll("s1", "CS201", 92); enroll("s1", "CS202", 75); enroll("s1", "CS203", 85)
    # Bala: CS201 55->6, CS202 30->0 FAIL, CS203 41->4
    enroll("s2", "CS201", 55); enroll("s2", "CS202", 30); enroll("s2", "CS203", 41)
    # Chitra (div B): CS201 81->9, CS202 not graded yet (enrolled only)
    enroll("s3", "CS201", 81); enroll("s3", "CS202")
    # Dev (3rd yr): CS301 70->8 ; plus an old backlog CS202 38 FAIL
    enroll("s4", "CS301", 70); enroll("s4", "CS202", 38)
    enroll("m1", "ME201", 99)

    def session(code, div, day, present_by_student):
        sid = c.run("INSERT INTO class_sessions (course_id,division_id,session_date,slot,created_at) VALUES (%s,%s,%s,1,%s)",
                    (cid[code], div, day, NOW))
        for stu, pres in present_by_student.items():
            c.run("INSERT INTO attendance_records (session_id,student_id,present) VALUES (%s,%s,%s)",
                  (sid, ids[stu], 1 if pres else 0))

    # division A (1): 4 sessions of CS201 — Asha 4/4, Bala 1/4 ; 2 sessions CS202 — Asha 2/2, Bala 1/2
    for i, (a, b) in enumerate([(1, 1), (1, 0), (1, 0), (1, 0)], start=1):
        session("CS201", 1, f"2026-01-0{i}", {"s1": a, "s2": b})
    for i, (a, b) in enumerate([(1, 1), (1, 0)], start=5):
        session("CS202", 1, f"2026-01-0{i}", {"s1": a, "s2": b})
    # division B (2): Chitra 2/4 in CS201
    for i, a in enumerate([1, 0, 1, 0], start=1):
        session("CS201", 2, f"2026-02-0{i}", {"s3": a})
    return ids, cid


_LOOP = asyncio.new_event_loop()


def run(coro):
    return _LOOP.run_until_complete(coro)


def U(ids, key, role, dept=None, yr=None, div=None):
    return {"user_id": ids[key], "role": role, "department_id": dept, "year_id": yr, "division_id": div}


def test_grading():
    assert grade_for(40, 100)["status"] == "PASS" and grade_for(39.9, 100)["status"] == "FAIL"
    assert grade_for(45, 50)["grade_point"] == 10


def test_cgpa_student_and_rollup():
    ids, _ = build()
    admin = U(ids, "super", "Administrator")
    r = run(rs.cgpa_report(admin, {"group_by": "student"}))
    by = {s["name"]: s for s in r["rows"]}
    # Asha: (4*10 + 2*8 + 3*9)/9 = 83/9 = 9.22 ; Bala: (4*6+0+3*4)/9 = 4.0
    assert by["Asha"]["cgpa"] == 9.22, by["Asha"]
    assert by["Bala"]["cgpa"] == 4.0 and by["Bala"]["backlogs"] == 1
    assert by["Chitra"]["cgpa"] == 9.0 and by["Chitra"]["courses"] == 1      # ungraded course ignored
    assert by["Dev"]["backlogs"] == 1
    assert "Old Senior" not in by and "Cara CR" not in by                    # no enrolments -> no rows
    # per division (dept x year x division)
    r = run(rs.cgpa_report(admin, {"group_by": "division", "department_id": 1}))
    g = {(x["year"], x["division"]): x for x in r["rows"]}
    assert g[("2nd Year", "A")]["avg_cgpa"] == round((9.22 + 4.0) / 2, 2) and g[("2nd Year", "A")]["students"] == 2
    assert g[("2nd Year", "B")]["avg_cgpa"] == 9.0
    # per department x year
    r = run(rs.cgpa_report(admin, {"group_by": "department_year"}))
    assert {(x["department"], x["year"]) for x in r["rows"]} == {("Computer Science", "2nd Year"), ("Computer Science", "3rd Year"), ("Mechanical", "2nd Year")}
    # per department / per year
    assert len(run(rs.cgpa_report(admin, {"group_by": "department"}))["rows"]) == 2
    assert len(run(rs.cgpa_report(admin, {"group_by": "year"}))["rows"]) == 2
    # SGPA for semester 3 only: Asha (4*10+2*8)/6 = 9.33
    r = run(rs.cgpa_report(admin, {"group_by": "student", "semester": 3, "department_id": 1, "year_id": 1}))
    assert {s["name"]: s["cgpa"] for s in r["rows"]}["Asha"] == 9.33 and r["metric"].startswith("SGPA")
    # cgpa_below filter
    r = run(rs.cgpa_report(admin, {"group_by": "student", "cgpa_below": 5}))
    assert [s["name"] for s in r["rows"]] == ["Bala"] or {s["name"] for s in r["rows"]} <= {"Bala", "Dev"}


def test_scoping():
    ids, _ = build()
    cr = U(ids, "cr", "CR", 1, 1, 1)
    r = run(rs.cgpa_report(cr, {"group_by": "student"}))
    assert {s["name"] for s in r["rows"]} == {"Asha", "Bala"}               # own division only
    for bad in ({"division_id": 2}, {"department_id": 2}):
        try:
            run(rs.cgpa_report(cr, bad)); assert False, "CR escaped scope"
        except rs.ReportError as e:
            assert e.status == 403
    # professor limited to department
    prof = U(ids, "prof", "Professor", 1)
    r = run(rs.cgpa_report(prof, {"group_by": "student"}))
    assert "Mech Kid" not in {s["name"] for s in r["rows"]}
    try:
        run(rs.cgpa_report(prof, {"department_id": 2})); assert False
    except rs.ReportError as e:
        assert e.status == 403
    # HOD (admin with dept) locked to own department
    hod = U(ids, "hod", "Administrator", 1)
    assert "Mech Kid" not in {s["name"] for s in run(rs.cgpa_report(hod, {"group_by": "student"}))["rows"]}
    # students / seniors cannot run reports
    for role in ("Student", "Senior", "Alumni", "Convener"):
        try:
            run(rs.backlog_report({"role": role, "department_id": 1}, {})); assert False
        except rs.ReportError as e:
            assert e.status == 403
    # CR without a division
    try:
        run(rs.cgpa_report({"role": "CR", "department_id": 1}, {})); assert False
    except rs.ReportError as e:
        assert e.status == 400


def test_course_average():
    ids, cid = build()
    admin = U(ids, "super", "Administrator")
    r = run(rs.course_average_report(admin, {"semester": 3, "department_id": 1}))
    by = {x["code"]: x for x in r["rows"]}
    # CS201 marks: 92, 55, 81 -> avg 76.0 ; 3 enrolled 3 graded, all pass
    assert by["CS201"]["avg_marks"] == 76.0 and by["CS201"]["pass_rate"] == 100.0
    # CS202 (sem 3): Asha 75, Bala 30, Chitra ungraded, Dev 38 -> graded 3, avg 47.67, passed 1, failed 2
    assert by["CS202"]["enrolled"] == 4 and by["CS202"]["graded"] == 3
    assert by["CS202"]["avg_marks"] == 47.67 and by["CS202"]["failed"] == 2
    assert "CS203" not in by and "ME201" not in by                           # other semester / department
    # division filter via CR: division A only -> CS201 avg of 92,55
    cr = U(ids, "cr", "CR", 1, 1, 1)
    r = run(rs.course_average_report(cr, {"semester": 3}))
    assert {x["code"]: x["avg_marks"] for x in r["rows"]}["CS201"] == 73.5
    # single course
    r = run(rs.course_average_report(admin, {"course_id": cid["CS203"]}))
    assert r["rows"][0]["avg_marks"] == 63.0
    # must give semester or course
    try:
        run(rs.course_average_report(admin, {})); assert False
    except rs.ReportError:
        pass
    # prof from another department cannot read a CSE course
    try:
        run(rs.course_average_report(U(ids, "prof_me", "Professor", 2), {"course_id": cid["CS201"]})); assert False
    except rs.ReportError as e:
        assert e.status == 403


def test_backlogs():
    ids, _ = build()
    admin = U(ids, "super", "Administrator")
    r = run(rs.backlog_report(admin, {}))
    assert {s["name"] for s in r["rows"]} == {"Bala", "Dev"}
    assert r["summary"] == {"students": 2, "total_backlogs": 2}
    assert "CS202" in r["rows"][0]["courses"]
    assert {s["name"] for s in run(rs.backlog_report(admin, {"year_id": 2}))["rows"]} == {"Dev"}
    assert run(rs.backlog_report(admin, {"semester": 4}))["rows"] == []
    assert run(rs.backlog_report(admin, {"min_backlogs": 2}))["rows"] == []
    assert {s["name"] for s in run(rs.backlog_report(U(ids, "cr", "CR", 1, 1, 1), {}))["rows"]} == {"Bala"}


def test_attendance_below():
    ids, cid = build()
    admin = U(ids, "super", "Administrator")
    # overall: Asha 6/6=100, Bala 2/6=33.3, Chitra 2/4=50
    names = lambda r: [(x["name"], x["percent"]) for x in r["rows"]]
    assert names(run(rs.attendance_below_report(admin, {"threshold": 75}))) == [("Bala", 33.3), ("Chitra", 50.0)]
    assert names(run(rs.attendance_below_report(admin, {"threshold": 50}))) == [("Bala", 33.3)]    # strictly less
    assert names(run(rs.attendance_below_report(admin, {"threshold": 50.1}))) == [("Bala", 33.3), ("Chitra", 50.0)]
    assert run(rs.attendance_below_report(admin, {"threshold": 0}))["rows"] == []
    assert len(run(rs.attendance_below_report(admin, {"threshold": 101 - 1}))["rows"]) == 2
    # per course: Bala CS201 1/4=25, CS202 1/2=50 ; threshold 40 -> only CS201
    r = run(rs.attendance_below_report(admin, {"threshold": 40, "mode": "per_course", "department_id": 1}))
    assert [(x["name"], x["course_code"], x["percent"]) for x in r["rows"]] == [("Bala", "CS201", 25.0)]
    # course filter + division scoping by CR
    cr = U(ids, "cr", "CR", 1, 1, 1)
    r = run(rs.attendance_below_report(cr, {"threshold": 75, "course_id": cid["CS202"]}))
    assert names(r) == [("Bala", 50.0)]
    # date range
    r = run(rs.attendance_below_report(admin, {"threshold": 75, "date_from": "2026-01-02", "date_to": "2026-01-04", "course_id": cid["CS201"]}))
    assert names(r) == [("Bala", 0.0)]
    # validation
    for bad in ({}, {"threshold": "abc"}, {"threshold": 120}, {"threshold": 50, "mode": "x"}, {"threshold": 50, "date_from": "01/02/2026"}):
        try:
            run(rs.attendance_below_report(admin, bad)); assert False, bad
        except rs.ReportError:
            pass


def test_imported_grade_only_results_and_official_cgpa():
    """Grade-only rows (no marks) + the sheet's cumulative CGPA, as produced by importer.loader."""
    import types
    from importer.loader import load
    c = sqlite_db.install(db)
    sheet = {"kind": "regular", "branch": "COMPUTER SCIENCE AND ENGINEERING", "semester_name": "SECOND",
             "courses": {"CS102 T": 4.0, "CS102 P": 1.0}, "course_names": {"CS102 T": "Data Structures", "CS102 P": "Data Structures"},
             "students": [
                 {"admission_no": "U25CS001", "name": "ASHA ROY", "semester": 2, "grades": {"CS102 T": "AA", "CS102 P": "BB"},
                  "credits": {}, "reg_credit": 5.0, "earned_credit": 5.0, "sgpa": 9.6, "cgpa": 8.5, "backlog_credits": 0},
                 {"admission_no": "U25CS002", "name": "BALA K", "semester": 2, "grades": {"CS102 T": "FF", "CS102 P": "XX"},
                  "credits": {}, "reg_credit": 5.0, "earned_credit": 0.0, "sgpa": 0.0, "cgpa": 4.0, "backlog_credits": 5}]}
    grad = dict(sheet, students=[{**sheet["students"][0], "admission_no": "U21CS009", "name": "OLD GRAD"}])
    st = run(load([(1, sheet), (4, grad)], log=lambda *a: None))
    assert st["users_new"] == 3 and st["alumni"] == 1 and st["results_new"] == 6
    assert run(load([(1, sheet), (4, grad)], log=lambda *a: None))["results_new"] == 0          # idempotent
    # year shift: 1st-year cohort is now 2nd year; the 4th-year cohort graduated
    yr = {r["roll_no"]: (r["role"], r["label"]) for r in c.all(
        "SELECT u.roll_no, u.role, y.label FROM users u LEFT JOIN academic_years y ON y.id=u.year_id")}
    assert yr["U25CS001"] == ("Student", "2nd Year") and yr["U21CS009"] == ("Alumni", None)
    admin = {"role": "Administrator", "department_id": None}
    r = run(rs.cgpa_report(admin, {"group_by": "student"}))
    assert {s["name"]: s["cgpa"] for s in r["rows"]} == {"Asha Roy": 8.5, "Bala K": 4.0}        # official cumulative CGPA
    r = run(rs.cgpa_report(admin, {"group_by": "student", "semester": 2}))
    assert {s["name"]: s["cgpa"] for s in r["rows"]}["Asha Roy"] == 9.6                          # SGPA recomputed from grades
    bl = run(rs.backlog_report(admin, {}))
    assert [s["name"] for s in bl["rows"]] == ["Bala K"] and "FF" in bl["rows"][0]["courses"]
    ca = run(rs.course_average_report(admin, {"semester": 2}))
    assert ca["rows"][0]["avg_marks"] is None and ca["rows"][0]["avg_grade_point"] is not None


if __name__ == "__main__":
    n = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn(); n += 1; print("ok  ", name)
    print(f"{n} tests passed")
