"""Role-scoped academic reports. No FastAPI imports here — raises ReportError instead,
so the same code is exercised by tests/test_reports_sqlite.py without a web stack.

Scope rules (resolve_scope):
  Administrator       -> any department/year/division; an Administrator whose own account
                         has a department (a H.O.D.) is locked to that department.
  Professor           -> own department only.
  CR / DCR            -> own department + year + division only.
  everyone else       -> 403.

Definitions
  CGPA   = SUM(credits * grade_point) / SUM(credits) over every graded course of a student
           (a failed course counts with grade point 0 until the result is corrected).
  SGPA   = same formula restricted to one semester (pass `semester`).
  Backlog= a result with status 'FAIL'.
  Attendance % = present marks / total marks in class_sessions' attendance_records.
           Students with no attendance records at all are not listed.
"""
from datetime import date

import db

STUDENT_ROLES = ("Student", "CR", "DCR")
_ROLE_IN = ",".join(["%s"] * len(STUDENT_ROLES))


class ReportError(Exception):
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.message = message
        self.status = status


# --------------------------------------------------------------------------- helpers
def _int(p: dict, key: str, required: bool = False, lo=None, hi=None):
    v = p.get(key)
    if v in (None, ""):
        if required:
            raise ReportError(f"'{key}' is required")
        return None
    try:
        n = int(v)
    except (TypeError, ValueError):
        raise ReportError(f"'{key}' must be an integer")
    if lo is not None and n < lo or hi is not None and n > hi:
        raise ReportError(f"'{key}' must be between {lo} and {hi}")
    return n


def _num(p: dict, key: str, required: bool = False, lo=None, hi=None):
    v = p.get(key)
    if v in (None, ""):
        if required:
            raise ReportError(f"'{key}' is required")
        return None
    try:
        n = float(v)
    except (TypeError, ValueError):
        raise ReportError(f"'{key}' must be a number")
    if lo is not None and n < lo or hi is not None and n > hi:
        raise ReportError(f"'{key}' must be between {lo} and {hi}")
    return n


def _date(p: dict, key: str):
    v = p.get(key)
    if not v:
        return None
    try:
        return date.fromisoformat(str(v)[:10]).isoformat()
    except ValueError:
        raise ReportError(f"'{key}' must be YYYY-MM-DD")


def resolve_scope(user: dict, p: dict) -> dict:
    """Return the effective {department_id, year_id, division_id} for this caller."""
    role = user.get("role")
    asked = {k: _int(p, k) for k in ("department_id", "year_id", "division_id")}

    if role == "Administrator":
        locked = {"department_id": user.get("department_id")} if user.get("department_id") else {}
    elif role == "Professor":
        if not user.get("department_id"):
            raise ReportError("Your account has no department assigned yet — ask the administrator.")
        locked = {"department_id": user["department_id"]}
    elif role in ("CR", "DCR"):
        if not (user.get("department_id") and user.get("year_id") and user.get("division_id")):
            raise ReportError("Your account has no division assigned yet — ask the administrator.")
        locked = {k: user[k] for k in ("department_id", "year_id", "division_id")}
    else:
        raise ReportError("Reports are available to Administrator, Professor, CR and DCR.", 403)

    scope = dict(asked)
    for k, v in locked.items():
        if asked[k] is not None and asked[k] != v:
            raise ReportError("That is outside your scope.", 403)
        scope[k] = v
    return scope


def _student_filter(scope: dict, alias: str = "u"):
    """WHERE fragments restricting students (alias.*) to the caller's scope."""
    sql = [f"{alias}.role IN ({_ROLE_IN})"]
    args = list(STUDENT_ROLES)
    for key in ("department_id", "year_id", "division_id"):
        if scope.get(key) is not None:
            sql.append(f"{alias}.{key} = %s")
            args.append(scope[key])
    return sql, args


async def _course_in_scope(course_id: int, scope: dict) -> dict:
    c = await db.one(
        "SELECT id, code, name, department_id, year_id, semester, credits, max_marks, professor_id "
        "FROM courses WHERE id=%s",
        (course_id,),
    )
    if not c:
        raise ReportError("Course not found", 404)
    if scope.get("department_id") is not None and c["department_id"] != scope["department_id"]:
        raise ReportError("That course is outside your scope.", 403)
    return c


def _f(v, nd=2):
    return None if v is None else round(float(v), nd)


# --------------------------------------------------------------------------- CGPA
GROUP_BYS = ("student", "department", "year", "department_year", "division")


async def cgpa_report(user: dict, p: dict) -> dict:
    scope = resolve_scope(user, p)
    group_by = (p.get("group_by") or "student").strip()
    if group_by not in GROUP_BYS:
        raise ReportError(f"group_by must be one of {', '.join(GROUP_BYS)}")
    semester = _int(p, "semester", lo=1, hi=12)
    below = _num(p, "cgpa_below", lo=0, hi=10)
    above = _num(p, "cgpa_above", lo=0, hi=10)

    where, args = _student_filter(scope)
    if semester is not None:
        where.append("c.semester = %s")
        args.append(semester)

    rows = await db.all(
        "SELECT u.id AS student_id, u.name, u.roll_no, "
        "       d.name AS department, y.label AS year, y.level_no AS year_no, dv.name AS division, "
        "       SUM(c.credits * r.grade_point) * 1.0 / SUM(c.credits) AS cgpa, "
        "       SUM(c.credits) AS credits, COUNT(*) AS courses, "
        "       SUM(CASE WHEN r.status = 'FAIL' THEN 1 ELSE 0 END) AS backlogs "
        "FROM users u "
        "JOIN enrollments e ON e.student_id = u.id "
        "JOIN courses c ON c.id = e.course_id "
        "JOIN results r ON r.enrollment_id = e.id "
        "LEFT JOIN departments d ON d.id = u.department_id "
        "LEFT JOIN academic_years y ON y.id = u.year_id "
        "LEFT JOIN divisions dv ON dv.id = u.division_id "
        "WHERE " + " AND ".join(where) + " "
        "GROUP BY u.id, u.name, u.roll_no, d.name, y.label, y.level_no, dv.name "
        "ORDER BY d.name, y.level_no, dv.name, u.name",
        tuple(args),
    )
    students = []
    for r in rows:
        cg = _f(r["cgpa"])
        if below is not None and not cg < below:
            continue
        if above is not None and not cg > above:
            continue
        students.append({
            "student_id": r["student_id"], "name": r["name"], "roll_no": r["roll_no"],
            "department": r["department"], "year": r["year"], "year_no": r["year_no"],
            "division": r["division"], "cgpa": cg, "credits": _f(r["credits"], 1),
            "courses": int(r["courses"]), "backlogs": int(r["backlogs"] or 0),
        })

    label = f"SGPA (semester {semester})" if semester else "CGPA"
    if group_by == "student":
        out_rows = sorted(students, key=lambda s: -s["cgpa"])
    else:
        def key(s):
            if group_by == "department":
                return (s["department"],)
            if group_by == "year":
                return (s["year_no"], s["year"])
            if group_by == "department_year":
                return (s["department"], s["year_no"], s["year"])
            return (s["department"], s["year_no"], s["year"], s["division"])  # division
        buckets = {}
        for s in students:
            buckets.setdefault(key(s), []).append(s)
        out_rows = []
        for k, members in sorted(buckets.items(), key=lambda kv: tuple((x is None, x) for x in kv[0])):
            vals = [m["cgpa"] for m in members]
            first = members[0]
            out_rows.append({
                "department": first["department"] if group_by != "year" else None,
                "year": first["year"] if group_by in ("year", "department_year", "division") else None,
                "division": first["division"] if group_by == "division" else None,
                "students": len(members),
                "avg_cgpa": round(sum(vals) / len(vals), 2),
                "min_cgpa": min(vals),
                "max_cgpa": max(vals),
                "students_with_backlogs": sum(1 for m in members if m["backlogs"] > 0),
            })
    overall = [s["cgpa"] for s in students]
    return {
        "report": "cgpa", "metric": label, "group_by": group_by,
        "scope": scope, "semester": semester,
        "summary": {"students": len(students),
                    "average": round(sum(overall) / len(overall), 2) if overall else None},
        "rows": out_rows,
    }


# --------------------------------------------------------------------------- course average
async def course_average_report(user: dict, p: dict) -> dict:
    scope = resolve_scope(user, p)
    course_id = _int(p, "course_id")
    semester = _int(p, "semester", lo=1, hi=12)
    if course_id is None and semester is None:
        raise ReportError("Pick a semester (and optionally a course).")
    if course_id is not None:
        await _course_in_scope(course_id, scope)

    where, args = _student_filter(scope)
    # restrict the *course* side to the caller's department as well
    if scope.get("department_id") is not None:
        where.append("c.department_id = %s")
        args.append(scope["department_id"])
    if course_id is not None:
        where.append("c.id = %s")
        args.append(course_id)
    if semester is not None:
        where.append("c.semester = %s")
        args.append(semester)

    rows = await db.all(
        "SELECT c.id AS course_id, c.code, c.name, c.semester, c.credits, c.max_marks, "
        "       d.name AS department, p.name AS professor, "
        "       COUNT(e.id) AS enrolled, COUNT(r.enrollment_id) AS graded, "
        "       AVG(r.marks_obtained) AS avg_marks, AVG(r.percentage) AS avg_pct, "
        "       MIN(r.marks_obtained) AS min_marks, MAX(r.marks_obtained) AS max_marks_scored, "
        "       SUM(CASE WHEN r.status = 'PASS' THEN 1 ELSE 0 END) AS passed, "
        "       SUM(CASE WHEN r.status = 'FAIL' THEN 1 ELSE 0 END) AS failed "
        "FROM courses c "
        "JOIN enrollments e ON e.course_id = c.id "
        "JOIN users u ON u.id = e.student_id "
        "LEFT JOIN results r ON r.enrollment_id = e.id "
        "LEFT JOIN departments d ON d.id = c.department_id "
        "LEFT JOIN users p ON p.id = c.professor_id "
        "WHERE " + " AND ".join(where) + " "
        "GROUP BY c.id, c.code, c.name, c.semester, c.credits, c.max_marks, d.name, p.name "
        "ORDER BY c.semester, c.code",
        tuple(args),
    )
    out = []
    for r in rows:
        graded = int(r["graded"])
        passed = int(r["passed"] or 0)
        out.append({
            "course_id": r["course_id"], "code": r["code"], "course": r["name"],
            "semester": r["semester"], "department": r["department"], "professor": r["professor"],
            "max_marks": r["max_marks"], "enrolled": int(r["enrolled"]), "graded": graded,
            "avg_marks": _f(r["avg_marks"]), "avg_percent": _f(r["avg_pct"]),
            "min_marks": _f(r["min_marks"]), "highest_marks": _f(r["max_marks_scored"]),
            "passed": passed, "failed": int(r["failed"] or 0),
            "pass_rate": round(passed * 100.0 / graded, 1) if graded else None,
        })
    return {"report": "course_average", "scope": scope, "semester": semester,
            "course_id": course_id, "summary": {"courses": len(out)}, "rows": out}


# --------------------------------------------------------------------------- backlogs
async def backlog_report(user: dict, p: dict) -> dict:
    scope = resolve_scope(user, p)
    semester = _int(p, "semester", lo=1, hi=12)
    course_id = _int(p, "course_id")
    min_backlogs = _int(p, "min_backlogs", lo=1, hi=50) or 1
    if course_id is not None:
        await _course_in_scope(course_id, scope)

    where, args = _student_filter(scope)
    where.append("r.status = 'FAIL'")
    if semester is not None:
        where.append("c.semester = %s")
        args.append(semester)
    if course_id is not None:
        where.append("c.id = %s")
        args.append(course_id)

    rows = await db.all(
        "SELECT u.id AS student_id, u.name, u.roll_no, d.name AS department, y.label AS year, "
        "       dv.name AS division, c.code, c.name AS course, c.semester, r.percentage "
        "FROM users u "
        "JOIN enrollments e ON e.student_id = u.id "
        "JOIN courses c ON c.id = e.course_id "
        "JOIN results r ON r.enrollment_id = e.id "
        "LEFT JOIN departments d ON d.id = u.department_id "
        "LEFT JOIN academic_years y ON y.id = u.year_id "
        "LEFT JOIN divisions dv ON dv.id = u.division_id "
        "WHERE " + " AND ".join(where) + " "
        "ORDER BY u.name, c.semester, c.code",
        tuple(args),
    )
    by_student = {}
    for r in rows:
        s = by_student.setdefault(r["student_id"], {
            "student_id": r["student_id"], "name": r["name"], "roll_no": r["roll_no"],
            "department": r["department"], "year": r["year"], "division": r["division"],
            "backlogs": 0, "courses": [],
        })
        s["backlogs"] += 1
        s["courses"].append(f"{r['code']} (sem {r['semester']}, {_f(r['percentage'], 1)}%)")
    out = [s for s in by_student.values() if s["backlogs"] >= min_backlogs]
    out.sort(key=lambda s: (-s["backlogs"], s["name"]))
    for s in out:
        s["courses"] = ", ".join(s["courses"])
    return {"report": "backlogs", "scope": scope, "semester": semester, "course_id": course_id,
            "summary": {"students": len(out), "total_backlogs": sum(s["backlogs"] for s in out)},
            "rows": out}


# --------------------------------------------------------------------------- attendance < x%
async def attendance_below_report(user: dict, p: dict) -> dict:
    scope = resolve_scope(user, p)
    threshold = _num(p, "threshold", required=True, lo=0, hi=100)
    mode = (p.get("mode") or "overall").strip()
    if mode not in ("overall", "per_course"):
        raise ReportError("mode must be 'overall' or 'per_course'")
    semester = _int(p, "semester", lo=1, hi=12)
    course_id = _int(p, "course_id")
    date_from, date_to = _date(p, "date_from"), _date(p, "date_to")
    if course_id is not None:
        await _course_in_scope(course_id, scope)

    where, args = _student_filter(scope)
    if semester is not None:
        where.append("c.semester = %s")
        args.append(semester)
    if course_id is not None:
        where.append("c.id = %s")
        args.append(course_id)
    if date_from:
        where.append("s.session_date >= %s")
        args.append(date_from)
    if date_to:
        where.append("s.session_date <= %s")
        args.append(date_to)

    per_course = mode == "per_course"
    sel_course = "c.code AS course_code, c.name AS course, " if per_course else ""
    grp_course = ", c.code, c.name" if per_course else ""
    rows = await db.all(
        "SELECT u.id AS student_id, u.name, u.roll_no, d.name AS department, y.label AS year, "
        "       dv.name AS division, " + sel_course +
        "       SUM(ar.present) AS attended, COUNT(*) AS total "
        "FROM attendance_records ar "
        "JOIN class_sessions s ON s.id = ar.session_id "
        "JOIN courses c ON c.id = s.course_id "
        "JOIN users u ON u.id = ar.student_id "
        "LEFT JOIN departments d ON d.id = u.department_id "
        "LEFT JOIN academic_years y ON y.id = u.year_id "
        "LEFT JOIN divisions dv ON dv.id = u.division_id "
        "WHERE " + " AND ".join(where) + " "
        "GROUP BY u.id, u.name, u.roll_no, d.name, y.label, dv.name" + grp_course + " "
        "HAVING SUM(ar.present) * 100.0 / COUNT(*) < %s "
        "ORDER BY SUM(ar.present) * 100.0 / COUNT(*), u.name",
        tuple(args) + (threshold,),
    )
    out = []
    for r in rows:
        attended, total = int(r["attended"] or 0), int(r["total"])
        row = {
            "student_id": r["student_id"], "name": r["name"], "roll_no": r["roll_no"],
            "department": r["department"], "year": r["year"], "division": r["division"],
            "attended": attended, "total": total,
            "percent": round(attended * 100.0 / total, 1),
        }
        if per_course:
            row["course_code"], row["course"] = r["course_code"], r["course"]
        out.append(row)
    return {"report": "attendance_below", "scope": scope, "threshold": threshold, "mode": mode,
            "semester": semester, "course_id": course_id,
            "summary": {"rows": len(out), "students": len({r["student_id"] for r in out})},
            "rows": out}
