from contextlib import closing
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import hashlib
import hmac
import secrets
import sqlite3

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Literal

DB = Path(__file__).with_name("study_shuttle.db")
LEGACY_SALT = b"study-shuttle-login-v1"
PASSWORD_ROUNDS = 180_000

app = FastAPI(title="Study Shuttle System", description="Student study tracking API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def connect():
    connection = sqlite3.connect(DB)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys=ON")
    return connection


def rows(sql, args=()):
    with closing(connect()) as connection:
        return [dict(row) for row in connection.execute(sql, args).fetchall()]


def hash_password(password):
    salt = secrets.token_bytes(16).hex()
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), bytes.fromhex(salt), PASSWORD_ROUNDS
    ).hex()
    return f"{salt}:{digest}"


def password_matches(password, stored_hash):
    if ":" in stored_hash:
        salt, expected = stored_hash.split(":", 1)
        candidate = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), bytes.fromhex(salt), PASSWORD_ROUNDS
        ).hex()
    else:
        expected = stored_hash
        candidate = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), LEGACY_SALT, PASSWORD_ROUNDS
        ).hex()
    return hmac.compare_digest(candidate, expected)


def create_login_session(connection, student_id):
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    expires_at = (datetime.now(timezone.utc) + timedelta(hours=12)).isoformat()
    connection.execute(
        "INSERT INTO login_session(token_hash, student_id, expires_at) VALUES(?,?,?)",
        (token_hash, student_id, expires_at),
    )
    return token


def initialize():
    with closing(connect()) as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS student(
                student_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL, program TEXT NOT NULL, semester INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS subject(
                subject_id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject_name TEXT NOT NULL, subject_code TEXT UNIQUE NOT NULL,
                difficulty_level TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS study_task(
                task_id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL REFERENCES student(student_id),
                subject_id INTEGER NOT NULL REFERENCES subject(subject_id),
                task_name TEXT NOT NULL, deadline TEXT,
                priority TEXT NOT NULL DEFAULT 'Medium',
                status TEXT NOT NULL DEFAULT 'Pending'
            );
            CREATE TABLE IF NOT EXISTS study_session(
                session_id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL REFERENCES student(student_id),
                subject_id INTEGER NOT NULL REFERENCES subject(subject_id),
                session_date TEXT NOT NULL, duration_minutes INTEGER NOT NULL,
                productivity INTEGER NOT NULL, notes TEXT DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS performance(
                performance_id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL REFERENCES student(student_id),
                subject_id INTEGER NOT NULL REFERENCES subject(subject_id),
                assessment_name TEXT NOT NULL, marks_obtained REAL NOT NULL,
                max_marks REAL NOT NULL, assessment_date TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS account(
                email TEXT PRIMARY KEY, full_name TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                student_id INTEGER UNIQUE REFERENCES student(student_id),
                username TEXT UNIQUE
            );
            CREATE TABLE IF NOT EXISTS student_subject(
                student_id INTEGER NOT NULL REFERENCES student(student_id) ON DELETE CASCADE,

subject_id INTEGER NOT NULL REFERENCES subject(subject_id) ON DELETE CASCADE,
                enrolled_on TEXT NOT NULL, PRIMARY KEY(student_id, subject_id)
            );
            CREATE TABLE IF NOT EXISTS difficulty(
                difficulty_id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL REFERENCES study_session(session_id) ON DELETE CASCADE,
                difficulty_type TEXT NOT NULL, description TEXT NOT NULL,
                severity TEXT NOT NULL, solved INTEGER NOT NULL DEFAULT 0,
                resolved_date TEXT
            );
            CREATE TABLE IF NOT EXISTS student_stress(
                stress_id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL REFERENCES student(student_id) ON DELETE CASCADE,
                session_id INTEGER REFERENCES study_session(session_id) ON DELETE SET NULL,
                stress_level INTEGER NOT NULL, reason TEXT NOT NULL,
                notes TEXT DEFAULT '', recorded_date TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS login_session(
                token_hash TEXT PRIMARY KEY,
                student_id INTEGER NOT NULL REFERENCES student(student_id) ON DELETE CASCADE,
                expires_at TEXT NOT NULL
            );
            """
        )

        # Migrate accounts created by the earlier single-login demo.
        account_columns = {row["name"] for row in connection.execute("PRAGMA table_info(account)")}
        if "student_id" not in account_columns:
            connection.execute(
                "ALTER TABLE account ADD COLUMN student_id INTEGER REFERENCES student(student_id)"
            )
        if "username" not in account_columns:
            connection.execute("ALTER TABLE account ADD COLUMN username TEXT")
        connection.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_account_student ON account(student_id)"
        )
        connection.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_account_username ON account(username)"
        )

        if connection.execute("SELECT COUNT(*) FROM student").fetchone()[0] == 0:
            connection.executemany(
                "INSERT INTO student(name,program,semester) VALUES(?,?,?)",
                [
                    ("Alice Johnson", "Computer Science", 3),
                    ("Ethan Miller", "Computer Science", 3),
                    ("Olivia Davis", "Information Technology", 2),
                ],
            )
        if connection.execute("SELECT COUNT(*) FROM subject").fetchone()[0] == 0:
            connection.executemany(
                "INSERT INTO subject(subject_name,subject_code,difficulty_level) VALUES(?,?,?)",
                [
                    ("Database Management Systems", "DBMS201", "Medium"),
                    ("Data Structures", "DS202", "Hard"),
                    ("Web Development", "WEB203", "Easy"),
                ],
            )
        if connection.execute("SELECT COUNT(*) FROM study_task").fetchone()[0] == 0:
            connection.executemany(
                "INSERT INTO study_task(student_id,subject_id,task_name,deadline,priority,status) VALUES(?,?,?,?,?,?)",
                [
                    (1, 1, "Practice SQL joins", "2026-11-02", "High", "Pending"),
                    (1, 2, "Revise linked lists", "2026-11-04", "Medium", "In Progress"),
                    (2, 1, "Complete normalization worksheet", "2026-11-01", "High", "Completed"),
                    (3, 3, "Build HTML form", "2026-11-05", "Low", "Pending"),
                    (2, 2, "Solve tree questions", "2026-11-06", "Medium", "Pending"),
                ],
            )
        if connection.execute("SELECT COUNT(*) FROM study_session").fetchone()[0] == 0:
            connection.executemany(
                "INSERT INTO study_session(student_id,subject_id,session_date,duration_minutes,productivity,notes) VALUES(?,?,?,?,?,?)",
                [
                    (1, 1, "2026-10-20", 50, 4, "Practised joins"),
                    (1, 2, "2026-10-21", 40, 3, "Reviewed linked lists"),
                    (2, 1, "2026-10-21", 60, 5, "Normalization practice"),
                    (3, 3, "2026-10-22", 35, 4, "Created a sample form"),
                ],
            )
        if connection.execute("SELECT COUNT(*) FROM performance").fetchone()[0] == 0:
            connection.executemany(
                "INSERT INTO performance(student_id,subject_id,assessment_name,marks_obtained,max_marks,assessment_date) VALUES(?,?,?,?,?,?)",
                [
                    (1, 1, "DBMS Quiz 1", 18, 20, "2026-10-15"),
                    (2, 1, "DBMS Quiz 1", 16, 20, "2026-10-15"),
                    (1, 2, "DS Quiz 1", 14, 20, "2026-10-16"),
                    (3, 3, "HTML Lab", 19, 20, "2026-10-17"),
                ],
            )

        # Keep the earlier presentation login, but attach it to Alice's student record.
        alice = connection.execute(
            "SELECT student_id,name FROM student ORDER BY student_id LIMIT 1"
        ).fetchone()
        legacy = connection.execute(
            "SELECT email,password_hash FROM account WHERE email='user1'"
        ).fetchone()
        if legacy and alice and not connection.execute(
            "SELECT 1 FROM account WHERE email='alice.johnson@studyshuttle.test'"
        ).fetchone():
            connection.execute(
                "UPDATE account SET email='alice.johnson@studyshuttle.test',full_name=?,student_id=?,username='user1' WHERE email='user1'",
                (alice["name"], alice["student_id"]),
            )

        students = connection.execute(
            "SELECT student_id,name FROM student ORDER BY student_id"
        ).fetchall()
        for student in students:
            if connection.execute(
                "SELECT 1 FROM account WHERE student_id=?", (student["student_id"],)
            ).fetchone():
                continue
            if student["student_id"] == alice["student_id"]:
                username, email, password = (
                    "user1",
                    "alice.johnson@studyshuttle.test",
                    "user1@12345",
                )
            else:
                username = f"student{student['student_id']}"
                email = f"student{student['student_id']}@studyshuttle.test"
                password = "study123"
            connection.execute(
                "INSERT OR IGNORE INTO account(email,full_name,password_hash,student_id,username) VALUES(?,?,?,?,?)",
                (email, student["name"], hash_password(password), student["student_id"], username),
            )

        # Convert existing task/session/assessment links into many-to-many enrollments.
        connection.execute(
            """
            INSERT OR IGNORE INTO student_subject(student_id,subject_id,enrolled_on)
            SELECT student_id,subject_id,date('now') FROM study_task
            UNION SELECT student_id,subject_id,date('now') FROM study_session
            UNION SELECT student_id,subject_id,date('now') FROM performance
            """
        )
        first_subject = connection.execute(
            "SELECT subject_id FROM subject ORDER BY subject_id LIMIT 1"
        ).fetchone()
        if first_subject:
            connection.execute(
                """
                INSERT OR IGNORE INTO student_subject(student_id,subject_id,enrolled_on)
                SELECT student_id,?,date('now') FROM student
                """,
                (first_subject["subject_id"],),
            )

        # Give every sample student at least one assessment row for the progress demo.
        for student in students:
            has_score = connection.execute(
                "SELECT 1 FROM performance WHERE student_id=?", (student["student_id"],)
            ).fetchone()
            if not has_score and first_subject:
                connection.execute(
                    "INSERT INTO performance(student_id,subject_id,assessment_name,marks_obtained,max_marks,assessment_date) VALUES(?,?,?,?,?,?)",
                    (student["student_id"], first_subject["subject_id"], "Practice Check", 15, 20, date.today().isoformat()),
                )

        if connection.execute("SELECT COUNT(*) FROM difficulty").fetchone()[0] == 0:
            for student in students:
                session_row = connection.execute(
                    "SELECT session_id FROM study_session WHERE student_id=? ORDER BY session_id LIMIT 1",
                    (student["student_id"],),
                ).fetchone()
                if session_row:
                    connection.execute(
                        "INSERT INTO difficulty(session_id,difficulty_type,description,severity,solved) VALUES(?,?,?,?,0)",
                        (session_row["session_id"], "Focus", "Had trouble staying focused during a study block.", "Medium"),
                    )
        if connection.execute("SELECT COUNT(*) FROM student_stress").fetchone()[0] == 0:
            for student in students:
                session_row = connection.execute(
                    "SELECT session_id FROM study_session WHERE student_id=? ORDER BY session_id LIMIT 1",
                    (student["student_id"],),
                ).fetchone()
                connection.execute(
                    "INSERT INTO student_stress(student_id,session_id,stress_level,reason,notes,recorded_date) VALUES(?,?,?,?,?,?)",
                    (student["student_id"], session_row["session_id"] if session_row else None, 4, "Course workload", "Fictional starter entry for the project demo.", date.today().isoformat()),
                )
        connection.commit()


initialize()


class LoginIn(BaseModel):
    username: str = Field(min_length=1, max_length=254)
    password: str = Field(min_length=1, max_length=200)


class RegistrationIn(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: str = Field(min_length=6, max_length=254)
    username: str = Field(min_length=3, max_length=30, pattern=r"^[A-Za-z0-9_.-]+$")
    program: str = Field(min_length=2, max_length=100)
    semester: int = Field(ge=1, le=12)
    password: str = Field(min_length=6, max_length=200)


class ProfileIn(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    program: str = Field(min_length=2, max_length=100)
    semester: int = Field(ge=1, le=12)


class EnrollmentIn(BaseModel):
    subject_id: int


class SubjectIn(BaseModel):
    subject_name: str = Field(min_length=2, max_length=100)
    subject_code: str = Field(min_length=2, max_length=20, pattern=r"^[A-Za-z0-9_-]+$")
    difficulty_level: Literal["Easy", "Medium", "Hard"] = "Medium"


class TaskIn(BaseModel):
    subject_id: int
    task_name: str = Field(min_length=2, max_length=160)
    deadline: str = ""
    priority: Literal["High", "Medium", "Low"] = "Medium"


class TaskStatusIn(BaseModel):
    status: Literal["Pending", "In Progress", "Completed"]


class SessionIn(BaseModel):
    subject_id: int
    session_date: str
    duration_minutes: int = Field(gt=0, le=1440)
    productivity: int = Field(ge=1, le=5)
    notes: str = Field(default="", max_length=500)


class DifficultyIn(BaseModel):
    session_id: int
    difficulty_type: str = Field(min_length=2, max_length=60)
    description: str = Field(min_length=3, max_length=500)
    severity: Literal["Low", "Medium", "High"]


class PerformanceIn(BaseModel):
    subject_id: int
    assessment_name: str = Field(min_length=2, max_length=120)
    marks_obtained: float = Field(ge=0)
    max_marks: float = Field(gt=0)
    assessment_date: str = Field(default_factory=lambda: date.today().isoformat())


class DifficultyUpdate(BaseModel):
    solved: bool


class StressIn(BaseModel):
    session_id: int | None = None
    stress_level: int = Field(ge=1, le=10)
    reason: str = Field(min_length=2, max_length=200)
    notes: str = Field(default="", max_length=500)
    recorded_date: str = Field(default_factory=lambda: date.today().isoformat())


def current_student(authorization: str | None = Header(default=None)):
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "Please sign in to continue.")
    token = authorization.split(" ", 1)[1].strip()
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    with closing(connect()) as connection:
        found = connection.execute(
            """
            SELECT s.student_id,s.name,s.program,s.semester,a.email,a.username
            FROM login_session ls
            JOIN student s USING(student_id)
            JOIN account a USING(student_id)
            WHERE ls.token_hash=? AND ls.expires_at>?
            """,
            (token_hash, datetime.now(timezone.utc).isoformat()),
        ).fetchone()
    if not found:
        raise HTTPException(401, "Your sign-in expired. Please sign in again.")
    return dict(found)


def require_enrollment(connection, student_id, subject_id):
    if not connection.execute(
        "SELECT 1 FROM student_subject WHERE student_id=? AND subject_id=?",
        (student_id, subject_id),
    ).fetchone():
        raise HTTPException(400, "Enroll in this subject before using it for a task or session.")


def require_owned_session(connection, student_id, session_id):
    if not connection.execute(
        "SELECT 1 FROM study_session WHERE session_id=? AND student_id=?",
        (session_id, student_id),
    ).fetchone():
        raise HTTPException(404, "Study session not found for this account.")


@app.get("/")
def root():
    return {"message": "Study Shuttle API is running", "database": "SQLite", "demo_data": True}


@app.post("/api/register")
def register(data: RegistrationIn):
    email, username = data.email.strip().lower(), data.username.strip().lower()
    name, program = data.name.strip(), data.program.strip()
    if "@" not in email or "." not in email.rsplit("@", 1)[-1]:
        raise HTTPException(400, "Enter a valid email address.")
    if len(name) < 2 or len(program) < 2:
        raise HTTPException(400, "Enter a name and program with at least 2 characters.")
    with closing(connect()) as connection:
        if connection.execute(
            "SELECT 1 FROM account WHERE lower(email)=? OR lower(username)=?",
            (email, username),
        ).fetchone():
            raise HTTPException(
409, "That email or username is already registered.")
        try:
            cursor = connection.execute(
                "INSERT INTO student(name,program,semester) VALUES(?,?,?)",
                (name, program, data.semester),
            )
            student_id = cursor.lastrowid
            connection.execute(
                "INSERT INTO account(email,full_name,password_hash,student_id,username) VALUES(?,?,?,?,?)",
                (email, name, hash_password(data.password), student_id, username),
            )
            token = create_login_session(connection, student_id)
            connection.commit()
        except sqlite3.IntegrityError:
            connection.rollback()
            raise HTTPException(409, "Could not create the account. Check that email and username are unique.")
    return {"token": token, "student_id": student_id, "name": name, "email": email, "username": username}


@app.post("/api/login")
def login(data: LoginIn):
    identifier = data.username.strip().lower()
    with closing(connect()) as connection:
        account = connection.execute(
            """
            SELECT email,full_name,password_hash,student_id,username FROM account
            WHERE lower(email)=? OR lower(username)=?
            """,
            (identifier, identifier),
        ).fetchone()
        if not account or not account["student_id"] or not password_matches(data.password, account["password_hash"]):
            raise HTTPException(401, "Username/email or password is incorrect.")
        token = create_login_session(connection, account["student_id"])
        if ":" not in account["password_hash"]:
            connection.execute(
                "UPDATE account SET password_hash=? WHERE email=?",
                (hash_password(data.password), account["email"]),
            )
        connection.commit()
    return {"token": token, "student_id": account["student_id"], "name": account["full_name"], "email": account["email"], "username": account["username"]}


@app.post("/api/logout")
def logout(authorization: str | None = Header(default=None), student=Depends(current_student)):
    token = authorization.split(" ", 1)[1].strip()
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    with closing(connect()) as connection:
        connection.execute("DELETE FROM login_session WHERE token_hash=?", (token_hash,))
        connection.commit()
    return {"message": "Signed out"}


@app.get("/api/me")
def my_profile(student=Depends(current_student)):
    return student


@app.put("/api/me")
def update_profile(data: ProfileIn, student=Depends(current_student)):
    name, program = data.name.strip(), data.program.strip()
    if len(name) < 2 or len(program) < 2:
        raise HTTPException(400, "Name and program must have at least 2 characters.")
    with closing(connect()) as connection:
        connection.execute(
            "UPDATE student SET name=?,program=?,semester=? WHERE student_id=?",
            (name, program, data.semester, student["student_id"]),
        )
        connection.execute(
            "UPDATE account SET full_name=? WHERE student_id=?", (name, student["student_id"])
        )
        connection.commit()
    return {"student_id": student["student_id"], "name": name, "program": program, "semester": data.semester}



@app.get("/api/dashboard")
def dashboard(student=Depends(current_student)):
    student_id = student["student_id"]
    counts = rows(
        """
        SELECT
          (SELECT COUNT(*) FROM student_subject WHERE student_id=?) subjects,
          (SELECT COUNT(*) FROM study_task WHERE student_id=?) tasks,
          (SELECT COUNT(*) FROM study_task WHERE student_id=? AND status!='Completed') pending,
          (SELECT COUNT(*) FROM study_session WHERE student_id=?) sessions,
          (SELECT COUNT(*) FROM difficulty d JOIN study_session ss USING(session_id)
             WHERE ss.student_id=? AND d.solved=0) open_difficulties,
          (SELECT COUNT(*) FROM performance WHERE student_id=?) assessments
        """,
        (student_id, student_id, student_id, student_id, student_id, student_id),
    )[0]
    recent = rows(
        """
        SELECT ss.session_date,sub.subject_name subject,ss.duration_minutes,ss.productivity
        FROM study_session ss JOIN subject sub USING(subject_id)
        WHERE ss.student_id=? ORDER BY ss.session_id DESC LIMIT 5
        """,
        (student_id,),
    )
    return {**counts, "recent": recent, "name": student["name"]}


@app.get("/api/subjects")
def subjects(student=Depends(current_student)):
    return rows(
        """
        SELECT sub.*,
          CASE WHEN enrollment.student_id IS NULL THEN 0 ELSE 1 END AS is_enrolled
        FROM subject sub
        LEFT JOIN student_subject enrollment
          ON enrollment.subject_id=sub.subject_id AND enrollment.student_id=?
        ORDER BY sub.subject_name
        """,
        (student["student_id"],),
    )


@app.post("/api/subjects")
def add_subject(data: SubjectIn, student=Depends(current_student)):
    name, code = data.subject_name.strip(), data.subject_code.strip().upper()
    if len(name) < 2:
        raise HTTPException(400, "Enter a subject name.")
    with closing(connect()) as connection:
        try:
            cursor = connection.execute(
                "INSERT INTO subject(subject_name,subject_code,difficulty_level) VALUES(?,?,?)",
                (name, code, data.difficulty_level),
            )
            subject_id = cursor.lastrowid
            connection.execute(
                "INSERT INTO student_subject(student_id,subject_id,enrolled_on) VALUES(?,?,?)",
                (student["student_id"], subject_id, date.today().isoformat()),
            )
            connection.commit()
        except sqlite3.IntegrityError:
            connection.rollback()
            raise HTTPException(409, "That subject code is already in use. Choose another code.")
    return {"message": "Subject added and enrolled.", "subject_id": subject_id}


@app.get("/api/enrollments")
def enrollments(student=Depends(current_student)):
    return rows(
        """
        SELECT sub.subject_id,sub.subject_name,sub.subject_code,sub.difficulty_level,enrollment.enrolled_on
        FROM student_subject enrollment JOIN subject sub USING(subject_id)
        WHERE enrollment.student_id=? ORDER BY sub.subject_name
        """,
        (student["student_id"],),
    )


@app.post("/api/enrollments")
def enroll(data: EnrollmentIn, student=Depends(current_student)):
    with closing(connect()) as connection:
        if not connection.execute(
            "SELECT 1 FROM subject WHERE subject_id=?", (data.subject_id,)
        ).fetchone():
            raise HTTPException(404, "Subject not found.")
        try:
            connection.execute(
                "INSERT INTO student_subject(student_id,subject_id,enrolled_on) VALUES(?,?,?)",
                (student["student_id"], data.subject_id, date.today().isoformat()),
            )
            connection.commit()
        except sqlite3.IntegrityError:
            raise HTTPException(409, "You are already enrolled in this subject.")
    return {"message": "Subject added to your subjects.", "subject_id": data.subject_id}


@app.get("/api/tasks")
def tasks(student=Depends(current_student)):
    return rows(
        """
        SELECT t.*,sub.subject_name subject FROM study_task t
        JOIN subject sub USING(subject_id)
        WHERE t.student_id=? ORDER BY t.task_id DESC
        """,
        (student["student_id"],),
    )


@app.post("/api/tasks")
def add_task(data: TaskIn, student=Depends(current_student)):
    task_name = data.task_name.strip()
    if len(task_name) < 2:
        raise HTTPException(400, "Task name must have at least 2 characters.")
    with closing(connect()) as connection:
        require_enrollment(connection, student["student_id"], data.subject_id)
        cursor = connection.execute(
            """
            INSERT INTO study_task(student_id,subject_id,task_name,deadline,priority,status)
            VALUES(?,?,?,?,?,'Pending')
            """,
            (student["student_id"], data.subject_id, task_name, data.deadline, data.priority),
        )
        connection.commit()
        return {"message": "Task created.", "task_id": cursor.lastrowid}


@app.patch("/api/tasks/{task_id}")
def update_task(task_id: int, data: TaskStatusIn, student=Depends(current_student)):
    with closing(connect()) as connection:
        cursor = connection.execute(
            "UPDATE study_task SET status=? WHERE task_id=? AND student_id=?",
            (data.status, task_id, student["student_id"]),
        )
        connection.commit()
        if not cursor.rowcount:
            raise HTTPException(404, "Task not found for this account.")
    return {"message": "Task updated."}


@app.delete("/api/tasks/{task_id}")
def delete_task(task_id: int, student=Depends(current_student)):
    with closing(connect()) as connection:
        cursor = connection.execute(
            "DELETE FROM study_task WHERE task_id=? AND student_id=?",
            (task_id, student["student_id"]),
        )
        connection.commit()
        if not cursor.rowcount:
            raise HTTPException(404, "Task not found for this account.")
    return {"message": "Task deleted."}


@app.get("/api/sessions")
def sessions(student=Depends(current_student)):
    return rows(
        """
        SELECT ss.*,sub.subject_name subject FROM study_session ss
        JOIN subject sub USING(subject_id)
        WHERE ss.student_id=? ORDER BY ss.session_id DESC
        """,
        (student["student_id"],),
    )


@app.post("/api/sessions")
def add_session(data: SessionIn, student=Depends(current_student)):
    with closing(connect()) as connection:
        require_enrollment(connection, student["student_id"], data.subject_id)
        cursor = connection.execute(
            """
            INSERT INTO study_session(student_id,subject_id,session_date,duration_minutes,productivity,notes)
            VALUES(?,?,?,?,?,?)
            """,
            (
                student["student_id"], data.subject_id, data.session_date,
                data.duration_minutes, data.productivity, data.notes.strip(),
            ),
        )
        connection.commit()
        return {"message": "Study session saved.", "session_id": cursor.lastrowid}


@app.get("/api/difficulties")
def difficulties(student=Depends(current_student)):
    return rows(
        """
        SELECT d.*,ss.session_date,sub.subject_name subject
        FROM difficulty d JOIN study_session ss USING(session_id)
        JOIN subject sub USING(subject_id)
        WHERE ss.student_id=? ORDER BY d.difficulty_id DESC
        """,
        (student["student_id"],),
    )


@app.post("/api/difficulties")
def add_difficulty(data: DifficultyIn, student=Depends(current_student)):
    with closing(connect()) as connection:
        require_owned_session(connection, student["student_id"], data.session_id)
        cursor = connection.execute(
            """
            INSERT INTO difficulty(session_id,difficulty_type,description,severity,solved)
            VALUES(?,?,?,?,0)
            """,
            (data.session_id, data.difficulty_type.strip(), data.description.strip(), data.severity),
        )
        connection.commit()
        return {"message": "Study difficulty recorded.", "difficulty_id": cursor.lastrowid}


@app.post("/api/performance")
def add_performance(data: PerformanceIn, student=Depends(current_student)):
    name = data.assessment_name.strip()
    if len(name) < 2:
        raise HTTPException(400, "Enter an assessment name.")
    if data.marks_obtained > data.max_marks:
        raise HTTPException(400, "Marks obtained cannot be greater than the maximum marks.")
    with closing(connect()) as connection:
        require_enrollment(connection, student["student_id"], data.subject_id)
        cursor = connection.execute(
            """
            INSERT INTO performance(student_id,subject_id,assessment_name,marks_obtained,max_marks,assessment_date)
            VALUES(?,?,?,?,?,?)
            """,
            (
                student["student_id"], data.subject_id, name,
                data.marks_obtained, data.max_marks, data.assessment_date,
            ),
        )
        connection.commit()
        return {"message": "Assessment score saved.", "performance_id": cursor.lastrowid}


@app.patch("/api/difficulties/{difficulty_id}")
def update_difficulty(difficulty_id: int, data: DifficultyUpdate, student=Depends(current_student)):
    with closing(connect()) as connection:
        cursor = connection.execute(
            """
            UPDATE difficulty SET solved=?,resolved_date=?
            WHERE difficulty_id=? AND session_id IN
              (SELECT session_id FROM study_session WHERE student_id=?)
            """,
            (
                int(data.solved), date.today().isoformat() if data.solved else None,
                difficulty_id, student["student_id"],
            ),
        )
        connection.commit()
        if not cursor.rowcount:
            raise HTTPException(404, "Difficulty record not found for this account.")
    return {"message": "Difficulty status updated."}


@app.get("/api/stress")
def stress_records(student=Depends(current_student)):
    return rows(
        """
        SELECT st.*,ss.session_date FROM student_stress st
        LEFT JOIN study_session ss USING(session_id)
        WHERE st.student_id=? ORDER BY st.stress_id DESC
        """,
        (student["student_id"],),
    )


@app.post("/api/stress")
def add_stress(data: StressIn, student=Depends(current_student)):
    with closing(connect()) as connection:
        if data.session_id is not None:
            require_owned_session(connection, student["student_id"], data.session_id)
        cursor = connection.execute(
            """
            INSERT INTO student_stress(student_id,session_id,stress_level,reason,notes,recorded_date)
            VALUES(?,?,?,?,?,?)
            """,
            (
                student["student_id"], data.session_id, data.stress_level,
                data.reason.strip(), data.notes.strip(), data.recorded_date,
            ),
        )
        connection.commit()
        return {"message": "Stress check-in saved.", "stress_id": cursor.lastrowid}


@app.get("/api/performance")
def performance(student=Depends(current_student)):
    return rows(
        """
        SELECT p.*,sub.subject_name subject,
               ROUND(100.0*p.marks_obtained/p.max_marks,1) percentage
        FROM performance p JOIN subject sub USING(subject_id)
        WHERE p.student_id=? ORDER BY p.assessment_date DESC
        """,
        (student["student_id"],),
    )


@app.get("/api/insights")
def insights(student=Depends(current_student)):
    student_id = student["student_id"]
    return {
        "subject_averages": rows(
            """
            SELECT sub.subject_name subject,
                   ROUND(AVG(p.marks_obtained*100.0/p.max_marks),1) average_percent,
                   COUNT(*) assessments
            FROM performance p JOIN subject sub USING(subject_id)
            WHERE p.student_id=? GROUP BY sub.subject_id ORDER BY average_percent DESC
            """,
            (student_id,),
        ),
        "study_totals": rows(
            """
            SELECT sub.subject_name subject,SUM(ss.duration_minutes) minutes,
                   ROUND(AVG(ss.productivity),1) avg_productivity
            FROM study_session ss JOIN subject sub USING(subject_id)
            WHERE ss.student_id=? GROUP BY sub.subject_id ORDER BY minutes DESC
            """,
            (student_id,),
        ),
        "pending_tasks": rows(
            """
            SELECT t.task_name,sub.subject_name subject,t.priority,t.deadline
            FROM study_task t JOIN subject sub USING(subject_id)
            WHERE t.student_id=? AND t.status!='Completed'
            ORDER BY CASE t.priority WHEN 'High' THEN 1 WHEN 'Medium' THEN 2 ELSE 3 END,
                     t.deadline
            """,
            (student_id,),
        ),
    }
