# Study Shuttle System

A simple student study-progress app with fictional student records, study tasks, study sessions, and academic performance summaries.

## Technology

- Frontend: React, Vite, and Axios
- Backend: Python and FastAPI
- Database: SQLite, stored locally in `backend/study_shuttle.db`

## Run on Windows

Install Python, Node.js, and Git. Open two PowerShell windows in this project folder.

### Window 1: backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn main:app --reload
```

### Window 2: frontend

```powershell
cd frontend
npm.cmd install
npm.cmd run dev
```

Open the local address Vite prints, usually http://localhost:5173. The API reference is at http://127.0.0.1:8000/docs.

## Sign-in for classroom presentation

Username: `user1`

Password: `user1@12345`

This is a local presentation sign-in only. Do not use it to protect real or private information.

## Presentation walkthrough

1. Sign in and show the Overview counts.
2. Open Students and add a fictional student. It will be selected automatically for the next task or study session.
3. Open Subjects and add a subject with a unique code. It will be selected automatically for the next task or study session.
4. Open Tasks and create a task, change its status, then delete it.
5. Open Study sessions and save a session.
6. Open Query results and show the populated academic and study summaries.
7. If asked how the website communicates with the backend, open `/docs` and show the API routes.

Each person who runs the project has their own local database. The current version is not an online shared site. The sample records are created automatically when the backend first starts. To reset them, stop the backend and delete `backend/study_shuttle.db`; it will be recreated at the next start.
