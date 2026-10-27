# AURA — Campus Commons (MySQL edition)

FastAPI + MySQL 8 backend, React frontend. Departments, years, divisions, courses, clubs and groups are
**entered by people in the UI** — nothing academic is hardcoded.

## Run it

```bash
# 1. database
mysql -u root -p -e "CREATE DATABASE aura CHARACTER SET utf8mb4"

# 2. backend
cd backend
pip install -r requirements.txt
cp .env.example .env            # set MYSQL_* and JWT_SECRET
uvicorn server:app --reload --port 8001
#   tables are created automatically on start (schema.sql), and a bootstrap
#   Administrator is created if none exists: ADMIN_EMAIL / ADMIN_PASSWORD (.env)

# 3. (optional) sample data: departments, divisions, courses, marks, attendance, demo logins
python seed_demo.py

# 4. frontend
cd ../frontend && yarn && yarn start
```

## First-time setup as Administrator (H.O.D.)
1. **Academic Setup → Departments, years & divisions** — add them (sign-up form reads these).
2. **Role Panel** — promote people to Professor / CR / DCR (self sign-up is Student / Senior / Alumni only).
3. **Academic Setup → Student placement** — set each student's department / year / division / roll no.
4. **Courses** — add courses (semester, credits, professor); **Enrolment** — enrol a whole division in a course.
5. Professors/CRs then use **Attendance & Marks**; reports fill up from that data.
6. **Clubs** — Administrator / Convener / Professor add clubs, cells and archive years.

## Reports (sidebar → Reports)
| Report | Parameters |
|---|---|
| CGPA / SGPA | department, year, division, semester (→ SGPA), group by student / department / year / department×year / division, GPA below/above |
| Course average | semester or a course (+ department / year / division): avg marks, avg %, min, max, pass rate |
| Backlogs | department, year, division, semester, course, min backlogs |
| Attendance below x% | any threshold (presets 75/60/50), overall or per course, semester, course, date range |

Visibility: **Administrator** — everything (an Administrator that has a department is a H.O.D. locked to it);
**Professor** — own department; **CR / DCR** — own division. CR/DCR can also mark class attendance for their division;
only the assigned Professor (or an Administrator) enters marks. Every report downloads as CSV.

Definitions: CGPA = Σ(credits × grade point) / Σ credits over graded courses (failed = 0 points);
grade scale and 40 % pass mark live in `backend/grading.py`; a failed result is a backlog.

## Tests
```bash
python3 backend/tests/test_reports_sqlite.py   # report SQL + scoping, no server/MySQL needed
pytest backend/tests                            # API tests against a running server (run seed_demo.py first)
```

## Deploy
- **Frontend → Vercel**: import the repo, Root Directory `frontend` (`vercel.json` is included), env var
  `REACT_APP_BACKEND_URL=https://<your-backend>`.
- **Backend → Render / Railway / Fly** (needs a long-running process for WebSockets): start with
  `uvicorn server:app --host 0.0.0.0 --port $PORT`; set `MYSQL_*`, `JWT_SECRET`, `ADMIN_EMAIL`, `ADMIN_PASSWORD`,
  and `FRONTEND_URL=https://<your-app>.vercel.app` (comma-separate several; optional `FRONTEND_ORIGIN_REGEX`
  such as `https://.*\.vercel\.app` for preview deployments).
- **Database**: any hosted MySQL 8; tables are created on first start.
