"""OPTIONAL sample data so every screen and report has something to show.

    python seed_demo.py            # idempotent: skips anything that already exists

Creates: 2 departments, 3 years, divisions, the 7 classic demo personas (same logins as before),
~12 students, courses with marks and class attendance. Clubs are NOT seeded — add them in the UI.
Never run this against a real deployment.
"""
import asyncio
import random
from datetime import date, timedelta

from dotenv import load_dotenv

load_dotenv()
import db  # noqa: E402
from common import hash_pw, now_utc, to_db  # noqa: E402
from grading import grade_for  # noqa: E402

PERSONAS = [  # name, email, password, role, dept, year, division
    ("Campus Admin", "admin@campus.edu", "admin123", "Administrator", None, None, None),
    ("Kavya Menon (CR)", "cr@campus.edu", "cr12345", "CR", "Computer Science", "3rd Year", "A"),
    ("Rohan Iyer (DCR)", "dcr@campus.edu", "dcr12345", "DCR", "Computer Science", "3rd Year", "A"),
    ("Prof. Alan Turing", "prof@campus.edu", "prof12345", "Professor", "Computer Science", None, None),
    ("Ananya Verma (Senior)", "senior@campus.edu", "senior12345", "Senior", "Computer Science", "4th Year", None),
    ("Ishaan Kapoor (Alumni)", "alumni@campus.edu", "alumni12345", "Alumni", "Computer Science", None, None),
    ("Freshie Student", "student@campus.edu", "student123", "Student", "Computer Science", "2nd Year", "A"),
]
COURSES = [  # code, name, credits, dept, year, sem
    ("CS301", "Database Management Systems", 4, "Computer Science", "3rd Year", 5),
    ("CS302", "Operating Systems", 4, "Computer Science", "3rd Year", 5),
    ("CS303", "Computer Networks", 3, "Computer Science", "3rd Year", 5),
    ("CS201", "Data Structures", 4, "Computer Science", "2nd Year", 3),
    ("EE301", "Control Systems", 3, "Electrical Engineering", "3rd Year", 5),
]


async def main():
    await db.init_pool()
    await db.ensure_schema()
    rnd = random.Random(7)
    ids = {}

    async def get_or(sql_sel, args, sql_ins, ins_args):
        r = await db.one(sql_sel, args)
        return r["id"] if r else await db.run(sql_ins, ins_args)

    for d, c in [("Computer Science", "CSE"), ("Electrical Engineering", "EE")]:
        ids[d] = await get_or("SELECT id FROM departments WHERE name=%s", (d,),
                              "INSERT INTO departments (name, code) VALUES (%s,%s)", (d, c))
    for i, y in enumerate(["1st Year", "2nd Year", "3rd Year", "4th Year"], start=1):
        ids[y] = await get_or("SELECT id FROM academic_years WHERE label=%s", (y,),
                              "INSERT INTO academic_years (label, level_no) VALUES (%s,%s)", (y, i))
    div = {}
    for d in ["Computer Science", "Electrical Engineering"]:
        for y in ["2nd Year", "3rd Year"]:
            for n in ["A", "B"]:
                div[(d, y, n)] = await get_or(
                    "SELECT id FROM divisions WHERE department_id=%s AND year_id=%s AND name=%s", (ids[d], ids[y], n),
                    "INSERT INTO divisions (department_id, year_id, name) VALUES (%s,%s,%s)", (ids[d], ids[y], n))

    async def user(name, email, pw, role, d, y, dv, roll=None):
        r = await db.one("SELECT id FROM users WHERE email=%s", (email,))
        if r:
            return r["id"]
        return await db.run(
            "INSERT INTO users (name,email,password_hash,role,department_id,year_id,division_id,roll_no,created_at) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (name, email, hash_pw(pw), role, ids.get(d), ids.get(y), div.get((d, y, dv)), roll, to_db(now_utc())))

    uid = {}
    for i, (n, e, p, r, d, y, dv) in enumerate(PERSONAS):
        uid[e] = await user(n, e, p, r, d, y, dv, roll=f"CS3{i:03d}" if r in ("CR", "DCR") else None)
    # extra 3rd-year CSE students, two divisions
    students = []
    first = ["Aarav", "Bhavna", "Chirag", "Diya", "Esha", "Farhan", "Gita", "Harsh", "Isha", "Jay"]
    for i, f in enumerate(first):
        dv = "A" if i < 5 else "B"
        students.append((await user(f"{f} S", f"{f.lower()}@campus.edu", "student123", "Student",
                                    "Computer Science", "3rd Year", dv, f"CS3{100 + i}"), dv))
    await db.run("UPDATE users SET roll_no='CS2001' WHERE email='student@campus.edu' AND roll_no IS NULL")

    cid = {}
    for code, name, cr, d, y, sem in COURSES:
        r = await db.one("SELECT id FROM courses WHERE code=%s", (code,))
        cid[code] = r["id"] if r else await db.run(
            "INSERT INTO courses (code,name,credits,max_marks,department_id,year_id,semester,professor_id) "
            "VALUES (%s,%s,%s,100,%s,%s,%s,%s)",
            (code, name, cr, ids[d], ids[y], sem, uid["prof@campus.edu"] if d == "Computer Science" else None))

    cohort = [(uid["cr@campus.edu"], "A"), (uid["dcr@campus.edu"], "A")] + [(s, dv) for s, dv in students]
    for code in ("CS301", "CS302", "CS303"):
        for sid, dv in cohort:
            if await db.one("SELECT id FROM enrollments WHERE student_id=%s AND course_id=%s", (sid, cid[code])):
                continue
            eid = await db.run("INSERT INTO enrollments (student_id, course_id) VALUES (%s,%s)", (sid, cid[code]))
            g = grade_for(max(0, min(100, rnd.gauss(62, 20))), 100)
            m = round(g["percentage"])
            g = grade_for(m, 100)
            await db.run(
                "INSERT INTO results (enrollment_id,marks_obtained,percentage,grade_point,grade_letter,status,updated_at) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s)",
                (eid, m, g["percentage"], g["grade_point"], g["grade_letter"], g["status"], to_db(now_utc())))
        if not await db.one("SELECT id FROM class_sessions WHERE course_id=%s LIMIT 1", (cid[code],)):
            for dv in ("A", "B"):
                members = [s for s, d in cohort if d == dv]
                for k in range(12):
                    day = (date.today() - timedelta(days=k * 2 + 1)).isoformat()
                    sid = await db.run(
                        "INSERT INTO class_sessions (course_id,division_id,session_date,slot,marked_by,created_at) "
                        "VALUES (%s,%s,%s,1,%s,%s)",
                        (cid[code], div[("Computer Science", "3rd Year", dv)], day, uid["prof@campus.edu"], to_db(now_utc())))
                    p = {s: rnd.random() for s in members}
                    await db.many("INSERT INTO attendance_records (session_id,student_id,present) VALUES (%s,%s,%s)",
                                  [(sid, s, 1 if rnd.random() < (0.45 + 0.5 * p[s]) else 0) for s in members])
    print("demo data ready")
    await db.close_pool()


if __name__ == "__main__":
    asyncio.run(main())
