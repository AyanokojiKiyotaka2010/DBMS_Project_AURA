-- AURA Campus — MySQL 8 schema
-- Applied automatically (idempotently) on server start, or manually:
--   mysql -u root -p < backend/schema.sql   (after CREATE DATABASE aura ...)
--
-- Conventions
--   * All timestamps are stored as UTC DATETIME; the API serialises them with a +00:00 offset.
--   * Every statement ends with ';' on its own line end and contains no ';' inside literals
--     (the bootstrap splits on ';').
--   * INDEX lines are always placed before FOREIGN KEY lines inside a CREATE TABLE.

-- ---------------------------------------------------------------------------
-- Academic structure (admin-managed — nothing is hardcoded in code any more)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS departments (
  id   INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(120) NOT NULL,
  code VARCHAR(20)  NULL,
  UNIQUE (name),
  UNIQUE (code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS academic_years (
  id       INT AUTO_INCREMENT PRIMARY KEY,
  label    VARCHAR(40) NOT NULL,
  level_no TINYINT     NOT NULL,
  UNIQUE (label),
  UNIQUE (level_no)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS divisions (
  id            INT AUTO_INCREMENT PRIMARY KEY,
  department_id INT NOT NULL,
  year_id       INT NOT NULL,
  name          VARCHAR(40) NOT NULL,
  UNIQUE (department_id, year_id, name),
  FOREIGN KEY (department_id) REFERENCES departments(id) ON DELETE CASCADE,
  FOREIGN KEY (year_id)       REFERENCES academic_years(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ---------------------------------------------------------------------------
-- Users
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
  id            INT AUTO_INCREMENT PRIMARY KEY,
  name          VARCHAR(120) NOT NULL,
  email         VARCHAR(190) NOT NULL,
  password_hash VARCHAR(100) NOT NULL,
  role          VARCHAR(20)  NOT NULL DEFAULT 'Student',
  department_id INT NULL,
  year_id       INT NULL,
  division_id   INT NULL,
  roll_no       VARCHAR(40) NULL,
  avatar        VARCHAR(500) NOT NULL DEFAULT '',
  created_at    DATETIME NOT NULL,
  UNIQUE (email),
  UNIQUE (roll_no),
  INDEX ix_users_scope (department_id, year_id, division_id),
  FOREIGN KEY (department_id) REFERENCES departments(id)    ON DELETE SET NULL,
  FOREIGN KEY (year_id)       REFERENCES academic_years(id) ON DELETE SET NULL,
  FOREIGN KEY (division_id)   REFERENCES divisions(id)      ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ---------------------------------------------------------------------------
-- Courses, enrolments, marks
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS courses (
  id            INT AUTO_INCREMENT PRIMARY KEY,
  code          VARCHAR(20)  NOT NULL,
  name          VARCHAR(160) NOT NULL,
  credits       DECIMAL(3,1) NOT NULL DEFAULT 3.0,
  max_marks     INT NOT NULL DEFAULT 100,
  department_id INT NOT NULL,
  year_id       INT NOT NULL,
  semester      TINYINT NOT NULL,
  professor_id  INT NULL,
  CONSTRAINT uq_course_code_dept UNIQUE (code, department_id),
  INDEX ix_courses_sem (department_id, year_id, semester),
  FOREIGN KEY (department_id) REFERENCES departments(id)    ON DELETE CASCADE,
  FOREIGN KEY (year_id)       REFERENCES academic_years(id) ON DELETE CASCADE,
  FOREIGN KEY (professor_id)  REFERENCES users(id)          ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS enrollments (
  id         INT AUTO_INCREMENT PRIMARY KEY,
  student_id INT NOT NULL,
  course_id  INT NOT NULL,
  UNIQUE (student_id, course_id),
  FOREIGN KEY (student_id) REFERENCES users(id)   ON DELETE CASCADE,
  FOREIGN KEY (course_id)  REFERENCES courses(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- One result per enrolment. Either entered as marks (grade derived by grading.py) or imported
-- grade-only from official result sheets (marks_obtained / percentage are then NULL).
CREATE TABLE IF NOT EXISTS results (
  enrollment_id  INT PRIMARY KEY,
  marks_obtained DECIMAL(6,2) NULL,
  percentage     DECIMAL(5,2) NULL,
  grade_point    DECIMAL(3,1) NOT NULL,
  grade_letter   VARCHAR(3)   NOT NULL,            -- AA..FF, or II / NA / XX (not passed)
  status         VARCHAR(4)   NOT NULL,            -- 'PASS' | 'FAIL'  (FAIL == backlog)
  updated_by     INT NULL,
  updated_at     DATETIME NOT NULL,
  INDEX ix_results_status (status),
  FOREIGN KEY (enrollment_id) REFERENCES enrollments(id) ON DELETE CASCADE,
  FOREIGN KEY (updated_by)    REFERENCES users(id)       ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Official per-semester summary printed on the result sheet (CGPA is cumulative over ALL
-- semesters, which individual course rows alone cannot reproduce).
CREATE TABLE IF NOT EXISTS semester_results (
  student_id     INT NOT NULL,
  semester       TINYINT NOT NULL,
  sgpa           DECIMAL(4,2) NOT NULL,
  cgpa           DECIMAL(4,2) NOT NULL,
  registered_credits DECIMAL(5,1) NOT NULL DEFAULT 0,
  earned_credits     DECIMAL(5,1) NOT NULL DEFAULT 0,
  PRIMARY KEY (student_id, semester),
  FOREIGN KEY (student_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ---------------------------------------------------------------------------
-- Official (class) attendance — marked by Professor / CR / DCR / Admin
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS class_sessions (
  id           INT AUTO_INCREMENT PRIMARY KEY,
  course_id    INT NOT NULL,
  division_id  INT NOT NULL,
  session_date DATE NOT NULL,
  slot         TINYINT NOT NULL DEFAULT 1,
  marked_by    INT NULL,
  created_at   DATETIME NOT NULL,
  UNIQUE (course_id, division_id, session_date, slot),
  FOREIGN KEY (course_id)   REFERENCES courses(id)   ON DELETE CASCADE,
  FOREIGN KEY (division_id) REFERENCES divisions(id) ON DELETE CASCADE,
  FOREIGN KEY (marked_by)   REFERENCES users(id)     ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS attendance_records (
  session_id INT NOT NULL,
  student_id INT NOT NULL,
  present    TINYINT(1) NOT NULL,
  PRIMARY KEY (session_id, student_id),
  INDEX ix_att_student (student_id),
  FOREIGN KEY (session_id) REFERENCES class_sessions(id) ON DELETE CASCADE,
  FOREIGN KEY (student_id) REFERENCES users(id)          ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Personal attendance tracker (existing "Attendance" screen: each user's own counters)
CREATE TABLE IF NOT EXISTS self_attendance (
  id       INT AUTO_INCREMENT PRIMARY KEY,
  user_id  INT NOT NULL,
  code     VARCHAR(40)  NOT NULL,
  name     VARCHAR(160) NOT NULL,
  attended INT NOT NULL DEFAULT 0,
  total    INT NOT NULL DEFAULT 0,
  INDEX ix_selfatt_user (user_id),
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ---------------------------------------------------------------------------
-- Announcements
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS announcements (
  id            INT AUTO_INCREMENT PRIMARY KEY,
  title         VARCHAR(255) NOT NULL,
  body          TEXT NOT NULL,
  kind          VARCHAR(30) NOT NULL DEFAULT 'general',
  deadline      DATETIME NULL,
  department_id INT NULL,
  year_id       INT NULL,
  author_id     INT NULL,
  author_name   VARCHAR(120) NOT NULL,
  author_role   VARCHAR(20)  NOT NULL,
  created_at    DATETIME NOT NULL,
  INDEX ix_ann_dept (department_id, created_at),
  FOREIGN KEY (department_id) REFERENCES departments(id)    ON DELETE SET NULL,
  FOREIGN KEY (year_id)       REFERENCES academic_years(id) ON DELETE SET NULL,
  FOREIGN KEY (author_id)     REFERENCES users(id)          ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ---------------------------------------------------------------------------
-- Anonymous queries
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS queries (
  id                  INT AUTO_INCREMENT PRIMARY KEY,
  department_id       INT NULL,
  topic               VARCHAR(120) NOT NULL DEFAULT 'General',
  query_text          TEXT NOT NULL,
  author_encrypted_id VARCHAR(40) NOT NULL,
  real_author_id      INT NULL,
  status              VARCHAR(12) NOT NULL DEFAULT 'Open',   -- Open | Answered | Resolved | Archived
  created_at          DATETIME NOT NULL,
  resolved_at         DATETIME NULL,
  INDEX ix_queries_status (status, created_at),
  FOREIGN KEY (department_id)  REFERENCES departments(id) ON DELETE SET NULL,
  FOREIGN KEY (real_author_id) REFERENCES users(id)       ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS query_answers (
  id          INT AUTO_INCREMENT PRIMARY KEY,
  query_id    INT NOT NULL,
  user_id     INT NULL,
  author_name VARCHAR(120) NOT NULL,
  role        VARCHAR(20)  NOT NULL,
  text        TEXT NOT NULL,
  created_at  DATETIME NOT NULL,
  INDEX ix_qa_query (query_id),
  FOREIGN KEY (query_id) REFERENCES queries(id) ON DELETE CASCADE,
  FOREIGN KEY (user_id)  REFERENCES users(id)   ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS query_attachments (
  id       INT AUTO_INCREMENT PRIMARY KEY,
  query_id INT NOT NULL,
  name     VARCHAR(80)  NOT NULL,
  mime     VARCHAR(100) NOT NULL,
  size     INT NOT NULL,
  data     LONGTEXT NOT NULL,
  INDEX ix_qatt_query (query_id),
  FOREIGN KEY (query_id) REFERENCES queries(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ---------------------------------------------------------------------------
-- Clubs (manually created — no seed data)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS clubs (
  id          INT AUTO_INCREMENT PRIMARY KEY,
  name        VARCHAR(160) NOT NULL,
  category    VARCHAR(80)  NOT NULL DEFAULT '',
  description TEXT NOT NULL,
  cover       VARCHAR(1000) NOT NULL DEFAULT '',
  created_by  INT NULL,
  created_at  DATETIME NOT NULL,
  UNIQUE (name),
  FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS club_cells (
  id      INT AUTO_INCREMENT PRIMARY KEY,
  club_id INT NOT NULL,
  name    VARCHAR(80) NOT NULL,
  UNIQUE (club_id, name),
  FOREIGN KEY (club_id) REFERENCES clubs(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS club_archives (
  club_id INT NOT NULL,
  year    SMALLINT NOT NULL,
  events  INT NOT NULL DEFAULT 0,
  PRIMARY KEY (club_id, year),
  FOREIGN KEY (club_id) REFERENCES clubs(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ---------------------------------------------------------------------------
-- Temporary groups
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS temp_groups (
  id           INT AUTO_INCREMENT PRIMARY KEY,
  name         VARCHAR(160) NOT NULL,
  creator_id   INT NULL,
  creator_name VARCHAR(120) NOT NULL,
  created_at   DATETIME NOT NULL,
  expires_at   DATETIME NOT NULL,
  INDEX ix_temp_expiry (expires_at),
  FOREIGN KEY (creator_id) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS temp_group_members (
  group_id INT NOT NULL,
  user_id  INT NOT NULL,
  PRIMARY KEY (group_id, user_id),
  FOREIGN KEY (group_id) REFERENCES temp_groups(id) ON DELETE CASCADE,
  FOREIGN KEY (user_id)  REFERENCES users(id)       ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ---------------------------------------------------------------------------
-- Complaints
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS complaints (
  id             INT AUTO_INCREMENT PRIMARY KEY,
  subject        VARCHAR(255) NOT NULL,
  body           TEXT NOT NULL,
  author_name    VARCHAR(120) NOT NULL,
  real_author_id INT NULL,
  status         VARCHAR(12) NOT NULL DEFAULT 'Open',        -- Open | Responded
  response       TEXT NOT NULL,
  created_at     DATETIME NOT NULL,
  responded_at   DATETIME NULL,
  INDEX ix_complaints_author (real_author_id),
  FOREIGN KEY (real_author_id) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS complaint_attachments (
  id           INT AUTO_INCREMENT PRIMARY KEY,
  complaint_id INT NOT NULL,
  name         VARCHAR(80)  NOT NULL,
  mime         VARCHAR(100) NOT NULL,
  size         INT NOT NULL,
  data         LONGTEXT NOT NULL,
  INDEX ix_catt_complaint (complaint_id),
  FOREIGN KEY (complaint_id) REFERENCES complaints(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
