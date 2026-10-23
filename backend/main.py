from contextlib import closing
from pathlib import Path
import sqlite3
import hashlib
import hmac
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

DB = Path(__file__).with_name('study_shuttle.db')
app = FastAPI(title='Study Shuttle System', description='Study progress API')
app.add_middleware(CORSMiddleware, allow_origins=['http://localhost:5173','http://127.0.0.1:5173'], allow_methods=['*'], allow_headers=['*'])

def connect():
    c=sqlite3.connect(DB); c.row_factory=sqlite3.Row; c.execute('PRAGMA foreign_keys=ON'); return c

def initialize():
    with closing(connect()) as c:
        c.executescript('''
        CREATE TABLE IF NOT EXISTS student(student_id INTEGER PRIMARY KEY, name TEXT NOT NULL, program TEXT NOT NULL, semester INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS subject(subject_id INTEGER PRIMARY KEY, subject_name TEXT NOT NULL, subject_code TEXT UNIQUE NOT NULL, difficulty_level TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS study_task(task_id INTEGER PRIMARY KEY AUTOINCREMENT, student_id INTEGER NOT NULL REFERENCES student, subject_id INTEGER NOT NULL REFERENCES subject, task_name TEXT NOT NULL, deadline TEXT, priority TEXT NOT NULL DEFAULT 'Medium', status TEXT NOT NULL DEFAULT 'Pending');
        CREATE TABLE IF NOT EXISTS study_session(session_id INTEGER PRIMARY KEY AUTOINCREMENT, student_id INTEGER NOT NULL REFERENCES student, subject_id INTEGER NOT NULL REFERENCES subject, session_date TEXT NOT NULL, duration_minutes INTEGER NOT NULL, productivity INTEGER NOT NULL, notes TEXT DEFAULT '');
        CREATE TABLE IF NOT EXISTS performance(performance_id INTEGER PRIMARY KEY AUTOINCREMENT, student_id INTEGER NOT NULL REFERENCES student, subject_id INTEGER NOT NULL REFERENCES subject, assessment_name TEXT NOT NULL, marks_obtained REAL NOT NULL, max_marks REAL NOT NULL, assessment_date TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS account(email TEXT PRIMARY KEY, full_name TEXT NOT NULL, password_hash TEXT NOT NULL);
        ''')
        if c.execute('SELECT COUNT(*) FROM student').fetchone()[0]==0:
            c.executemany('INSERT INTO student VALUES(?,?,?,?)',[(1,'Alice Johnson','Computer Science',3),(2,'Ethan Miller','Computer Science',3),(3,'Olivia Davis','Information Technology',2)])
            c.executemany('INSERT INTO subject VALUES(?,?,?,?)',[(1,'Database Management Systems','DBMS201','Medium'),(2,'Data Structures','DS202','Hard'),(3,'Web Development','WEB203','Easy')])
            c.executemany('INSERT INTO study_task(student_id,subject_id,task_name,deadline,priority,status) VALUES(?,?,?,?,?,?)',[(1,1,'Practice SQL joins','2026-11-02','High','Pending'),(1,2,'Revise linked lists','2026-11-04','Medium','In Progress'),(2,1,'Complete normalization worksheet','2026-11-01','High','Completed'),(3,3,'Build HTML form','2026-11-05','Low','Pending'),(2,2,'Solve tree questions','2026-11-06','Medium','Pending')])
            c.executemany('INSERT INTO study_session(student_id,subject_id,session_date,duration_minutes,productivity,notes) VALUES(?,?,?,?,?,?)',[(1,1,'2026-10-20',50,4,'Practised joins'),(1,2,'2026-10-21',40,3,'Reviewed linked lists'),(2,1,'2026-10-21',60,5,'Normalization practice'),(3,3,'2026-10-22',35,4,'Created a sample form')])
            c.executemany('INSERT INTO performance(student_id,subject_id,assessment_name,marks_obtained,max_marks,assessment_date) VALUES(?,?,?,?,?,?)',[(1,1,'DBMS Quiz 1',18,20,'2026-10-15'),(2,1,'DBMS Quiz 1',16,20,'2026-10-15'),(1,2,'DS Quiz 1',14,20,'2026-10-16'),(3,3,'HTML Lab',19,20,'2026-10-17')])
            c.commit()
        salt = b'study-shuttle-login-v1'
        password_hash = hashlib.pbkdf2_hmac('sha256', b'user1@12345', salt, 180000).hex()
        c.execute('INSERT OR IGNORE INTO account(email,full_name,password_hash) VALUES(?,?,?)', ('user1','Student User',password_hash))
        c.execute("DELETE FROM account WHERE email != 'user1'")
        c.commit()

initialize()
class LoginIn(BaseModel):
    username: str
    password: str

class StudentIn(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    program: str = Field(min_length=2, max_length=100)
    semester: int = Field(ge=1)

class TaskIn(BaseModel):
    student_id:int; subject_id:int; task_name:str=Field(min_length=2, max_length=160); deadline:str=''; priority:str='Medium'; status:str='Pending'
class SubjectIn(BaseModel):
    subject_name: str = Field(min_length=2, max_length=100)
    subject_code: str = Field(min_length=2, max_length=20)
    difficulty_level: str = Field(pattern='^(Easy|Medium|Hard)$')
class SessionIn(BaseModel):
    student_id:int; subject_id:int; session_date:str; duration_minutes:int=Field(gt=0); productivity:int=Field(ge=1,le=5); notes:str=''

def rows(sql,args=()):
    with closing(connect()) as c: return [dict(r) for r in c.execute(sql,args).fetchall()]
@app.get('/')
def root(): return {'message':'Study Shuttle API is running','database':'SQLite database','sample_data':True}
@app.post('/api/login')
def login(data: LoginIn):
    account = rows('SELECT email, full_name, password_hash FROM account WHERE email=?', (data.username.strip().lower(),))
    candidate = hashlib.pbkdf2_hmac('sha256', data.password.encode(), b'study-shuttle-login-v1', 180000).hex()
    if not account or not hmac.compare_digest(candidate, account[0]['password_hash']):
        raise HTTPException(status_code=401, detail='Email or password is incorrect')
    return {'name': account[0]['full_name'], 'email': account[0]['email']}

@app.get('/api/dashboard')
def dashboard():
    return {'students':rows('SELECT COUNT(*) n FROM student')[0]['n'],'subjects':rows('SELECT COUNT(*) n FROM subject')[0]['n'],'tasks':rows('SELECT COUNT(*) n FROM study_task')[0]['n'],'sessions':rows('SELECT COUNT(*) n FROM study_session')[0]['n'],'pending':rows("SELECT COUNT(*) n FROM study_task WHERE status!='Completed'")[0]['n'],'recent':rows('SELECT ss.session_date, s.name student, sub.subject_name subject, ss.duration_minutes, ss.productivity FROM study_session ss JOIN student s USING(student_id) JOIN subject sub USING(subject_id) ORDER BY ss.session_id DESC LIMIT 5')}
@app.get('/api/students')
def students(): return rows('SELECT * FROM student ORDER BY student_id')
@app.post('/api/students')
def add_student(x: StudentIn):
    name, program = x.name.strip(), x.program.strip()
    if len(name) < 2 or len(program) < 2:
        raise HTTPException(400, 'Enter a student name and program with at least 2 characters.')
    with closing(connect()) as c:
        cur = c.execute('INSERT INTO student(name,program,semester) VALUES(?,?,?)', (name, program, x.semester))
        c.commit()
        return {'message': 'Student added', 'student_id': cur.lastrowid}

@app.get('/api/subjects')
def subjects(): return rows('SELECT * FROM subject ORDER BY subject_id')
@app.post('/api/subjects')
def add_subject(x: SubjectIn):
    name, code = x.subject_name.strip(), x.subject_code.strip().upper()
    if len(name) < 2 or len(code) < 2:
        raise HTTPException(400, 'Enter a subject name and code with at least 2 characters.')
    with closing(connect()) as c:
        try:
            cur = c.execute('INSERT INTO subject(subject_name,subject_code,difficulty_level) VALUES(?,?,?)', (name, code, x.difficulty_level))
            c.commit()
        except sqlite3.IntegrityError:
            raise HTTPException(409, 'That subject code is already in use. Choose a different code.')
        return {'message': 'Subject added', 'subject_id': cur.lastrowid}
@app.get('/api/tasks')
def tasks(): return rows('SELECT t.*, s.name student, sub.subject_name subject FROM study_task t JOIN student s USING(student_id) JOIN subject sub USING(subject_id) ORDER BY t.task_id DESC')
@app.post('/api/tasks')
def add_task(x:TaskIn):
    with closing(connect()) as c:
        try:
            cur=c.execute('INSERT INTO study_task(student_id,subject_id,task_name,deadline,priority,status) VALUES(?,?,?,?,?,?)',(x.student_id,x.subject_id,x.task_name.strip(),x.deadline,x.priority,x.status)); c.commit()
        except sqlite3.IntegrityError:
            raise HTTPException(400, 'Choose a student and subject that still exist, then try again.')
        return {'message':'Task created','task_id':cur.lastrowid}
@app.patch('/api/tasks/{task_id}')
def update_task(task_id:int,status:str):
    with closing(connect()) as c:
        cur=c.execute('UPDATE study_task SET status=? WHERE task_id=?',(status,task_id)); c.commit()
        if not cur.rowcount: raise HTTPException(404,'Task not found')
        return {'message':'Task updated'}
@app.delete('/api/tasks/{task_id}')
def delete_task(task_id:int):
    with closing(connect()) as c:
        cur=c.execute('DELETE FROM study_task WHERE task_id=?',(task_id,)); c.commit()
        if not cur.rowcount: raise HTTPException(404,'Task not found')
        return {'message':'Task deleted'}
@app.get('/api/sessions')
def sessions(): return rows('SELECT ss.*, s.name student, sub.subject_name subject FROM study_session ss JOIN student s USING(student_id) JOIN subject sub USING(subject_id) ORDER BY ss.session_id DESC')
@app.post('/api/sessions')
def add_session(x:SessionIn):
    with closing(connect()) as c:
        try:
            cur=c.execute('INSERT INTO study_session(student_id,subject_id,session_date,duration_minutes,productivity,notes) VALUES(?,?,?,?,?,?)',(x.student_id,x.subject_id,x.session_date,x.duration_minutes,x.productivity,x.notes)); c.commit()
        except sqlite3.IntegrityError:
            raise HTTPException(400, 'Choose a student and subject that still exist, then try again.')
        return {'message':'Study session saved','session_id':cur.lastrowid}
@app.get('/api/performance')
def performance(): return rows('SELECT p.*, s.name student, sub.subject_name subject, ROUND(100.0*p.marks_obtained/p.max_marks,1) percentage FROM performance p JOIN student s USING(student_id) JOIN subject sub USING(subject_id) ORDER BY p.assessment_date DESC')
@app.get('/api/insights')
def insights():
    return {'subject_averages':rows('SELECT sub.subject_name subject, ROUND(AVG(p.marks_obtained*100.0/p.max_marks),1) average_percent, COUNT(*) assessments FROM performance p JOIN subject sub USING(subject_id) GROUP BY sub.subject_id ORDER BY average_percent DESC'),'study_totals':rows('SELECT sub.subject_name subject, SUM(ss.duration_minutes) minutes, ROUND(AVG(ss.productivity),1) avg_productivity FROM study_session ss JOIN subject sub USING(subject_id) GROUP BY sub.subject_id ORDER BY minutes DESC'),'pending_tasks':rows("SELECT t.task_name, s.name student, sub.subject_name subject, t.priority, t.deadline FROM study_task t JOIN student s USING(student_id) JOIN subject sub USING(subject_id) WHERE t.status!='Completed' ORDER BY CASE t.priority WHEN 'High' THEN 1 WHEN 'Medium' THEN 2 ELSE 3 END, t.deadline")}
