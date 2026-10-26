# Study Shuttle System

A student self-service study tracker with fictional demo records.

## Technology

- Frontend: React, Vite, and Axios
- Backend: Python and FastAPI
- Database: SQLite, stored locally in `backend/study_shuttle.db`

## Run on Windows

Install Python and Node.js, then open two PowerShell windows in the project folder.

### Backend window

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn main:app --reload
```

### Frontend window

```powershell
cd frontend
npm.cmd install
npm.cmd run dev
```

Open the local address Vite prints, usually http://localhost:5173. The API reference is at http://127.0.0.1:8000/docs.

## Demo student accounts

- Username `user1`, password `user1@12345` (Alice Johnson)
- Username `student2`, password `study123` (Ethan Miller)
- Username `student3`, password `study123` (Olivia Davis)

Other existing fictional students receive `student<ID>` usernames with the same demo password. New students can create their own account from the sign-in page.

## Student workflow

1. Sign in or create a student account.
2. Browse subjects and enroll in one or more.
3. Create tasks for an enrolled subject and update task status.
4. Log study sessions for enrolled subjects.
5. Record study difficulties and stress check-ins.
6. View personal performance and study summaries in Progress.

The app scopes tasks, sessions, difficulties, stress records, performance, and summaries to the signed-in student. Demo accounts use fictional records. This classroom sign-in is for local demonstration only, not production security. See `docs/ER-Diagram.md` for the implemented data relationships.

Each computer keeps its own local database; this is not a shared online site. The database initializes sample records on first run and preserves existing records during schema upgrades.
