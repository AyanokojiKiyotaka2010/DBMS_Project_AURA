"""Academic data that used to be hardcoded or absent — now entered by people:

  Administrator (H.O.D.)  departments, years, divisions, courses, student placement, enrolment
  Professor               marks for the courses they teach, class attendance for those courses
  CR / DCR                class attendance for their own division
Everything is plain relational data (see schema.sql); reports.py reads it back.
"""
from datetime import date, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

import db
from common import STUDENT_ROLES, fetch_user, get_user, now_utc, require_role, to_db, user_public
from grading import grade_for

router = APIRouter()
_ROLE_IN = ",".join(["%s"] * len(STUDENT_ROLES))


# ----------------------------------------------------------------- schemas
class DepartmentIn(BaseModel):
    name: str
    code: Optional[str] = None


class YearIn(BaseModel):
    label: str
    level_no: int


class DivisionIn(BaseModel):
    department_id: int
    year_id: int
    name: str


class CourseIn(BaseModel):
    code: str
    name: str
    credits: float = 3
    max_marks: int = 100
    department_id: int
    year_id: int
    semester: int
    professor_id: Optional[int] = None


class CourseUpdate(BaseModel):
    name: Optional[str] = None
    credits: Optional[float] = None
    semester: Optional[int] = None
    professor_id: Optional[int] = None


class AssignmentIn(BaseModel):
    department_id: Optional[int] = None
    year_id: Optional[int] = None
    division_id: Optional[int] = None
    roll_no: Optional[str] = None


class EnrollIn(BaseModel):
    course_id: int
    division_id: Optional[int] = None
    student_ids: Optional[List[int]] = None


class UnenrollIn(BaseModel):
    course_id: int
    student_id: int


class MarkEntry(BaseModel):
    student_id: int
    marks_obtained: Optional[float] = None       # null / omitted -> clear the result


class ResultsIn(BaseModel):
    entries: List[MarkEntry]


class AttendanceIn(BaseModel):
    division_id: int
    date: str
    slot: int = 1
    present_student_ids: List[int] = []


# ----------------------------------------------------------------- public structure
async def structure() -> dict:
    depts = await db.all("SELECT id, name, code FROM departments ORDER BY name")
    years = await db.all("SELECT id, label, level_no FROM academic_years ORDER BY level_no")
    divs = await db.all(
        "SELECT dv.id, dv.name, dv.department_id, dv.year_id, d.name AS department, y.label AS year "
        "FROM divisions dv JOIN departments d ON d.id = dv.department_id "
        "JOIN academic_years y ON y.id = dv.year_id ORDER BY d.name, y.level_no, dv.name")
    return {"departments": depts, "years": years, "divisions": divs}


# ----------------------------------------------------------------- admin: structure CRUD
def _admin(user):
    require_role(user, ["Administrator"])


@router.post("/admin/departments")
async def add_department(inp: DepartmentIn, user=Depends(get_user)):
    _admin(user)
    name, code = inp.name.strip(), (inp.code or "").strip() or None
    if not name:
        raise HTTPException(400, "Department name is required")
    if await db.one("SELECT id FROM departments WHERE name=%s", (name,)):
        raise HTTPException(400, "Department already exists")
    if code and await db.one("SELECT id FROM departments WHERE code=%s", (code,)):
        raise HTTPException(400, "Department code already used")
    await db.run("INSERT INTO departments (name, code) VALUES (%s,%s)", (name, code))
    return await structure()


@router.delete("/admin/departments/{dept_id}")
async def delete_department(dept_id: int, user=Depends(get_user)):
    _admin(user)
    n_users = (await db.one("SELECT COUNT(*) AS n FROM users WHERE department_id=%s", (dept_id,)))["n"]
    n_courses = (await db.one("SELECT COUNT(*) AS n FROM courses WHERE department_id=%s", (dept_id,)))["n"]
    if n_users or n_courses:
        raise HTTPException(409, f"Department still has {n_users} user(s) and {n_courses} course(s) — "
                                 "move or delete them first.")
    await db.run("DELETE FROM departments WHERE id=%s", (dept_id,))      # divisions cascade (they hold no users)
    return await structure()


@router.post("/admin/years")
async def add_year(inp: YearIn, user=Depends(get_user)):
    _admin(user)
    label = inp.label.strip()
    if not label or inp.level_no < 1 or inp.level_no > 10:
        raise HTTPException(400, "Label required and level_no must be 1-10")
    if await db.one("SELECT id FROM academic_years WHERE label=%s OR level_no=%s", (label, inp.level_no)):
        raise HTTPException(400, "A year with that label or level number already exists")
    await db.run("INSERT INTO academic_years (label, level_no) VALUES (%s,%s)", (label, inp.level_no))
    return await structure()


@router.delete("/admin/years/{year_id}")
async def delete_year(year_id: int, user=Depends(get_user)):
    _admin(user)
    n_users = (await db.one("SELECT COUNT(*) AS n FROM users WHERE year_id=%s", (year_id,)))["n"]
    n_courses = (await db.one("SELECT COUNT(*) AS n FROM courses WHERE year_id=%s", (year_id,)))["n"]
    if n_users or n_courses:
        raise HTTPException(409, f"Year still has {n_users} user(s) and {n_courses} course(s).")
    await db.run("DELETE FROM academic_years WHERE id=%s", (year_id,))
    return await structure()


@router.post("/admin/divisions")
async def add_division(inp: DivisionIn, user=Depends(get_user)):
    _admin(user)
    name = inp.name.strip()
    if not name:
        raise HTTPException(400, "Division name is required")
    if not await db.one("SELECT id FROM departments WHERE id=%s", (inp.department_id,)):
        raise HTTPException(400, "Unknown department")
    if not await db.one("SELECT id FROM academic_years WHERE id=%s", (inp.year_id,)):
        raise HTTPException(400, "Unknown year")
    if await db.one("SELECT id FROM divisions WHERE department_id=%s AND year_id=%s AND name=%s",
                    (inp.department_id, inp.year_id, name)):
        raise HTTPException(400, "That division already exists")
    await db.run("INSERT INTO divisions (department_id, year_id, name) VALUES (%s,%s,%s)",
                 (inp.department_id, inp.year_id, name))
    return await structure()


@router.delete("/admin/divisions/{division_id}")
async def delete_division(division_id: int, user=Depends(get_user)):
    _admin(user)
    n = (await db.one("SELECT COUNT(*) AS n FROM users WHERE division_id=%s", (division_id,)))["n"]
    if n:
        raise HTTPException(409, f"Division still has {n} student(s).")
    await db.run("DELETE FROM divisions WHERE id=%s", (division_id,))
    return await structure()


# ----------------------------------------------------------------- admin: people placement
@router.put("/admin/users/{uid}/assignment")
async def assign_user(uid: int, inp: AssignmentIn, user=Depends(get_user)):
    """Set a person's department / year / division / roll number. Only the fields present in the
    request body change; send null to clear one."""
    _admin(user)
    cur = await db.one("SELECT id, department_id, year_id, division_id, roll_no FROM users WHERE id=%s", (uid,))
    if not cur:
        raise HTTPException(404, "User not found")
    merged = {k: cur[k] for k in ("department_id", "year_id", "division_id", "roll_no")}
    for k in inp.model_fields_set:
        merged[k] = getattr(inp, k)
    if isinstance(merged["roll_no"], str):
        merged["roll_no"] = merged["roll_no"].strip() or None
    if merged["department_id"] is not None and not await db.one("SELECT id FROM departments WHERE id=%s", (merged["department_id"],)):
        raise HTTPException(400, "Unknown department")
    if merged["year_id"] is not None and not await db.one("SELECT id FROM academic_years WHERE id=%s", (merged["year_id"],)):
        raise HTTPException(400, "Unknown year")
    if merged["division_id"] is not None:
        dv = await db.one("SELECT department_id, year_id FROM divisions WHERE id=%s", (merged["division_id"],))
        if not dv:
            raise HTTPException(400, "Unknown division")
        if dv["department_id"] != merged["department_id"] or dv["year_id"] != merged["year_id"]:
            raise HTTPException(400, "Division does not belong to that department / year")
    if merged["roll_no"] and await db.one("SELECT id FROM users WHERE roll_no=%s AND id<>%s", (merged["roll_no"], uid)):
        raise HTTPException(400, "Roll number already used")
    await db.run("UPDATE users SET department_id=%s, year_id=%s, division_id=%s, roll_no=%s WHERE id=%s",
                 (merged["department_id"], merged["year_id"], merged["division_id"], merged["roll_no"], uid))
    return {"ok": True, "user": user_public(await fetch_user("u.id=%s", (uid,)))}


# ----------------------------------------------------------------- courses
_COURSE_SELECT = (
    "SELECT c.id, c.code, c.name, c.credits, c.max_marks, c.department_id, c.year_id, c.semester, c.professor_id, "
    "       d.name AS department, y.label AS year, p.name AS professor "
    "FROM courses c JOIN departments d ON d.id = c.department_id JOIN academic_years y ON y.id = c.year_id "
    "LEFT JOIN users p ON p.id = c.professor_id "
)


def _course_out(c: dict) -> dict:
    return {**c, "credits": float(c["credits"])}


@router.get("/courses")
async def list_courses(department_id: Optional[int] = None, year_id: Optional[int] = None,
                       semester: Optional[int] = None, mine: bool = False, user=Depends(get_user)):
    role = user["role"]
    if role not in ("Administrator", "Professor", "CR", "DCR"):
        raise HTTPException(403, "Not available for your role")
    where, args = [], []
    if role == "Professor":
        department_id = user["department_id"]
        if mine:
            where.append("c.professor_id = %s")
            args.append(int(user["user_id"]))
    elif role in ("CR", "DCR"):
        department_id = user["department_id"]
    elif role == "Administrator" and user["department_id"]:
        department_id = user["department_id"]            # a H.O.D. only sees their own department
    for col, val in (("c.department_id", department_id), ("c.year_id", year_id), ("c.semester", semester)):
        if val is not None:
            where.append(f"{col} = %s")
            args.append(val)
    sql = _COURSE_SELECT + ("WHERE " + " AND ".join(where) + " " if where else "") + "ORDER BY d.name, y.level_no, c.semester, c.code"
    return [_course_out(c) for c in await db.all(sql, tuple(args))]


async def _validate_course_refs(dept_id, year_id, semester, professor_id):
    if dept_id is not None and not await db.one("SELECT id FROM departments WHERE id=%s", (dept_id,)):
        raise HTTPException(400, "Unknown department")
    if year_id is not None and not await db.one("SELECT id FROM academic_years WHERE id=%s", (year_id,)):
        raise HTTPException(400, "Unknown year")
    if semester is not None and not 1 <= semester <= 12:
        raise HTTPException(400, "semester must be between 1 and 12")
    if professor_id is not None:
        p = await db.one("SELECT role FROM users WHERE id=%s", (professor_id,))
        if not p or p["role"] != "Professor":
            raise HTTPException(400, "professor_id must be a user with the Professor role")


@router.post("/admin/courses")
async def add_course(inp: CourseIn, user=Depends(get_user)):
    _admin(user)
    code, name = inp.code.strip().upper(), inp.name.strip()
    if not code or not name:
        raise HTTPException(400, "Course code and name are required")
    if inp.credits <= 0 or inp.credits > 20 or inp.max_marks <= 0:
        raise HTTPException(400, "credits must be in (0, 20] and max_marks positive")
    await _validate_course_refs(inp.department_id, inp.year_id, inp.semester, inp.professor_id)
    if await db.one("SELECT id FROM courses WHERE code=%s AND department_id=%s", (code, inp.department_id)):
        raise HTTPException(400, "That department already has a course with this code")
    cid = await db.run(
        "INSERT INTO courses (code,name,credits,max_marks,department_id,year_id,semester,professor_id) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
        (code, name, inp.credits, inp.max_marks, inp.department_id, inp.year_id, inp.semester, inp.professor_id))
    return _course_out(await db.one(_COURSE_SELECT + "WHERE c.id=%s", (cid,)))


@router.put("/admin/courses/{course_id}")
async def update_course(course_id: int, inp: CourseUpdate, user=Depends(get_user)):
    _admin(user)
    cur = await db.one("SELECT id FROM courses WHERE id=%s", (course_id,))
    if not cur:
        raise HTTPException(404, "Course not found")
    changes = {k: getattr(inp, k) for k in inp.model_fields_set}
    if "name" in changes and not (changes["name"] or "").strip():
        raise HTTPException(400, "Course name cannot be empty")
    if "credits" in changes and (changes["credits"] is None or changes["credits"] <= 0 or changes["credits"] > 20):
        raise HTTPException(400, "credits must be in (0, 20]")
    await _validate_course_refs(None, None, changes.get("semester"), changes.get("professor_id"))
    if changes:
        sets = ", ".join(f"{k}=%s" for k in changes)         # keys limited to the pydantic model fields
        await db.run(f"UPDATE courses SET {sets} WHERE id=%s", tuple(changes.values()) + (course_id,))
    return _course_out(await db.one(_COURSE_SELECT + "WHERE c.id=%s", (course_id,)))


@router.delete("/admin/courses/{course_id}")
async def delete_course(course_id: int, force: bool = False, user=Depends(get_user)):
    _admin(user)
    n = (await db.one("SELECT COUNT(*) AS n FROM enrollments WHERE course_id=%s", (course_id,)))["n"]
    if n and not force:
        raise HTTPException(409, f"{n} student(s) are enrolled; deleting would also erase their marks and "
                                 "attendance for this course. Retry with ?force=true to confirm.")
    await db.run("DELETE FROM courses WHERE id=%s", (course_id,))
    return {"ok": True}


# ----------------------------------------------------------------- enrolment
@router.post("/admin/enrollments")
async def enroll(inp: EnrollIn, user=Depends(get_user)):
    _admin(user)
    if not await db.one("SELECT id FROM courses WHERE id=%s", (inp.course_id,)):
        raise HTTPException(404, "Course not found")
    if inp.division_id is None and not inp.student_ids:
        raise HTTPException(400, "Give a division_id or a list of student_ids")
    added = 0
    if inp.division_id is not None:
        added += await db.rowcount(
            "INSERT INTO enrollments (student_id, course_id) "
            "SELECT u.id, %s FROM users u WHERE u.division_id = %s AND u.role IN (" + _ROLE_IN + ") "
            "AND NOT EXISTS (SELECT 1 FROM enrollments e WHERE e.student_id = u.id AND e.course_id = %s)",
            (inp.course_id, inp.division_id) + tuple(STUDENT_ROLES) + (inp.course_id,))
    for sid in inp.student_ids or []:
        ok = await db.one(f"SELECT id FROM users WHERE id=%s AND role IN ({_ROLE_IN})", (sid,) + tuple(STUDENT_ROLES))
        if not ok:
            raise HTTPException(400, f"User {sid} is not a student")
        if not await db.one("SELECT id FROM enrollments WHERE student_id=%s AND course_id=%s", (sid, inp.course_id)):
            await db.run("INSERT INTO enrollments (student_id, course_id) VALUES (%s,%s)", (sid, inp.course_id))
            added += 1
    total = (await db.one("SELECT COUNT(*) AS n FROM enrollments WHERE course_id=%s", (inp.course_id,)))["n"]
    return {"ok": True, "enrolled_now": added, "total_enrolled": total}


@router.post("/admin/enrollments/remove")
async def unenroll(inp: UnenrollIn, user=Depends(get_user)):
    _admin(user)
    n = await db.rowcount("DELETE FROM enrollments WHERE course_id=%s AND student_id=%s", (inp.course_id, inp.student_id))
    if not n:
        raise HTTPException(404, "Enrolment not found")
    return {"ok": True}


# ----------------------------------------------------------------- course access rules
async def _course_access(user: dict, course_id: int, *, write: str = None, division_id: int = None) -> dict:
    """Load a course and enforce who may touch it.
    write=None        read roster
    write='results'   enter marks     (Administrator, or the Professor assigned to the course)
    write='attendance'                (Administrator, assigned Professor, CR/DCR of that division)"""
    c = await db.one(_COURSE_SELECT + "WHERE c.id=%s", (course_id,))
    if not c:
        raise HTTPException(404, "Course not found")
    role = user["role"]
    if role == "Administrator":
        if user["department_id"] and user["department_id"] != c["department_id"]:
            raise HTTPException(403, "That course belongs to another department")
    elif role == "Professor":
        if user["department_id"] != c["department_id"]:
            raise HTTPException(403, "That course belongs to another department")
        if write and c["professor_id"] != int(user["user_id"]):
            raise HTTPException(403, "Only the professor assigned to this course can do that")
    elif role in ("CR", "DCR"):
        if write == "results":
            raise HTTPException(403, "CR / DCR cannot enter marks")
        if user["department_id"] != c["department_id"] or user["division_id"] is None:
            raise HTTPException(403, "That course is outside your division")
        if division_id is not None and division_id != user["division_id"]:
            raise HTTPException(403, "You can only work with your own division")
    else:
        raise HTTPException(403, "Not available for your role")
    return c


@router.get("/courses/{course_id}/divisions")
async def course_divisions(course_id: int, user=Depends(get_user)):
    """Divisions that currently have students enrolled in this course (drives the pickers)."""
    c = await _course_access(user, course_id)
    rows = await db.all(
        "SELECT dv.id AS division_id, dv.name AS division, y.label AS year, COUNT(*) AS students "
        "FROM enrollments e JOIN users u ON u.id = e.student_id "
        "JOIN divisions dv ON dv.id = u.division_id JOIN academic_years y ON y.id = dv.year_id "
        "WHERE e.course_id = %s " + ("AND dv.id = %s " if user["role"] in ("CR", "DCR") else "") +
        "GROUP BY dv.id, dv.name, y.label ORDER BY y.label, dv.name",
        (course_id,) + ((user["division_id"],) if user["role"] in ("CR", "DCR") else ()))
    return {"course": _course_out(c), "divisions": rows}


# ----------------------------------------------------------------- marks
@router.get("/courses/{course_id}/roster")
async def roster(course_id: int, division_id: Optional[int] = None, user=Depends(get_user)):
    c = await _course_access(user, course_id, division_id=division_id)
    if user["role"] in ("CR", "DCR"):
        division_id = user["division_id"]
    sql = ("SELECT u.id AS student_id, u.name, u.roll_no, dv.name AS division, e.id AS enrollment_id, "
           "       r.marks_obtained, r.percentage, r.grade_point, r.grade_letter, r.status "
           "FROM enrollments e JOIN users u ON u.id = e.student_id "
           "LEFT JOIN divisions dv ON dv.id = u.division_id "
           "LEFT JOIN results r ON r.enrollment_id = e.id WHERE e.course_id = %s ")
    args = [course_id]
    if division_id is not None:
        sql += "AND u.division_id = %s "
        args.append(division_id)
    rows = await db.all(sql + "ORDER BY u.roll_no, u.name", tuple(args))
    for r in rows:
        for k in ("marks_obtained", "percentage", "grade_point"):
            if r[k] is not None:
                r[k] = float(r[k])
    return {"course": _course_out(c), "students": rows}


@router.post("/courses/{course_id}/results")
async def save_results(course_id: int, inp: ResultsIn, user=Depends(get_user)):
    c = await _course_access(user, course_id, write="results")
    if not inp.entries:
        raise HTTPException(400, "No entries")
    enrol = {r["student_id"]: r["id"] for r in await db.all(
        "SELECT id, student_id FROM enrollments WHERE course_id=%s", (course_id,))}
    problems, plan = [], []
    for e in inp.entries:
        eid = enrol.get(e.student_id)
        if eid is None:
            problems.append(f"student {e.student_id} is not enrolled in {c['code']}")
        elif e.marks_obtained is None:
            plan.append((eid, None))
        else:
            try:
                plan.append((eid, {"marks": e.marks_obtained, **grade_for(e.marks_obtained, c["max_marks"])}))
            except ValueError as ex:
                problems.append(f"student {e.student_id}: {ex}")
    if problems:                                   # all-or-nothing: nothing is saved if any row is bad
        raise HTTPException(400, "; ".join(problems[:10]))
    now = to_db(now_utc())
    saved = cleared = 0
    async with db.transaction() as tx:
        for eid, g in plan:
            await tx.run("DELETE FROM results WHERE enrollment_id=%s", (eid,))
            if g is None:
                cleared += 1
                continue
            await tx.run(
                "INSERT INTO results (enrollment_id,marks_obtained,percentage,grade_point,grade_letter,status,updated_by,updated_at) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                (eid, g["marks"], g["percentage"], g["grade_point"], g["grade_letter"], g["status"],
                 int(user["user_id"]), now))
            saved += 1
    return {"ok": True, "saved": saved, "cleared": cleared}


# ----------------------------------------------------------------- class attendance
def _parse_day(s: str) -> date:
    try:
        d = date.fromisoformat(str(s)[:10])
    except ValueError:
        raise HTTPException(400, "date must be YYYY-MM-DD")
    if d > now_utc().date() + timedelta(days=1):
        raise HTTPException(400, "Cannot mark attendance for a future date")
    return d


@router.get("/courses/{course_id}/attendance-sheet")
async def attendance_sheet(course_id: int, division_id: int, date: str, slot: int = 1, user=Depends(get_user)):
    c = await _course_access(user, course_id, write="attendance", division_id=division_id)
    day = _parse_day(date)
    sess = await db.one("SELECT id FROM class_sessions WHERE course_id=%s AND division_id=%s AND session_date=%s AND slot=%s",
                        (course_id, division_id, day.isoformat(), slot))
    rows = await db.all(
        "SELECT u.id AS student_id, u.name, u.roll_no, ar.present "
        "FROM enrollments e JOIN users u ON u.id = e.student_id "
        "LEFT JOIN attendance_records ar ON ar.student_id = u.id AND ar.session_id = %s "
        "WHERE e.course_id = %s AND u.division_id = %s ORDER BY u.roll_no, u.name",
        (sess["id"] if sess else -1, course_id, division_id))
    return {"course": _course_out(c), "division_id": division_id, "date": day.isoformat(), "slot": slot,
            "already_marked": bool(sess),
            "students": [{"student_id": r["student_id"], "name": r["name"], "roll_no": r["roll_no"],
                          "present": None if r["present"] is None else bool(r["present"])} for r in rows]}


@router.post("/courses/{course_id}/attendance")
async def mark_class_attendance(course_id: int, inp: AttendanceIn, user=Depends(get_user)):
    """Create (or overwrite) one class session. Everyone enrolled from that division is recorded:
    listed ids as present, the rest as absent."""
    await _course_access(user, course_id, write="attendance", division_id=inp.division_id)
    day = _parse_day(inp.date)
    if inp.slot < 1 or inp.slot > 12:
        raise HTTPException(400, "slot must be between 1 and 12")
    if not await db.one("SELECT id FROM divisions WHERE id=%s", (inp.division_id,)):
        raise HTTPException(400, "Unknown division")
    students = [r["id"] for r in await db.all(
        "SELECT u.id FROM enrollments e JOIN users u ON u.id = e.student_id "
        "WHERE e.course_id = %s AND u.division_id = %s", (course_id, inp.division_id))]
    if not students:
        raise HTTPException(400, "No students from that division are enrolled in this course")
    present = set(inp.present_student_ids)
    stray = present - set(students)
    if stray:
        raise HTTPException(400, f"Not enrolled / not in this division: {sorted(stray)[:10]}")
    async with db.transaction() as tx:
        old = await tx.one("SELECT id FROM class_sessions WHERE course_id=%s AND division_id=%s AND session_date=%s AND slot=%s",
                           (course_id, inp.division_id, day.isoformat(), inp.slot))
        if old:
            await tx.run("DELETE FROM attendance_records WHERE session_id=%s", (old["id"],))
            sid = old["id"]
            await tx.run("UPDATE class_sessions SET marked_by=%s WHERE id=%s", (int(user["user_id"]), sid))
        else:
            sid = await tx.run(
                "INSERT INTO class_sessions (course_id,division_id,session_date,slot,marked_by,created_at) "
                "VALUES (%s,%s,%s,%s,%s,%s)",
                (course_id, inp.division_id, day.isoformat(), inp.slot, int(user["user_id"]), to_db(now_utc())))
        await tx.many("INSERT INTO attendance_records (session_id,student_id,present) VALUES (%s,%s,%s)",
                      [(sid, s, 1 if s in present else 0) for s in students])
    return {"ok": True, "session_id": sid, "present": len(present), "absent": len(students) - len(present),
            "total": len(students), "overwritten": bool(old)}
