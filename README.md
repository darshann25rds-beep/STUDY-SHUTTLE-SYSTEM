# Study Shuttle System

A small, formal study progress project. It uses simulated students and a local SQLite database so you can run it without installing PostgreSQL. The database is created and sample records are added automatically the first time the API starts.

## Start it on Windows

Install Python 3.10 or newer, Node.js, and GitHub Desktop. Open this project folder in File Explorer. Start two PowerShell windows in the folder `STUDY-SHUTTLE-SYSTEM-main`.

### Window 1: API

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn main:app --reload
```

Leave this window open. The API is at http://127.0.0.1:8000. Its interactive API guide is at http://127.0.0.1:8000/docs.

### Window 2: Website

```powershell
cd frontend
npm install
npm run dev
```

Open the local website address printed by Vite, usually http://localhost:5173.

## Sign-in account

Username: `user1`

Password: `user1@12345`

This local sign-in is for classroom presentation only.

## Presentation walkthrough

1. Sign in with the account above, then open **Overview** and show the sample student, subject, task, and session totals.
2. Open **Tasks**, add a task, change its status, then delete it to projectnstrate create, update, and delete.
3. Open **Study sessions** and save a simulated session.
4. Open **Query results** to show populated summaries for marks, study time, productivity, and pending tasks.
5. If asked how the website communicates with the backend, open `/docs` and show the API endpoints.

The sample records are fictional. The local database file is `backend/study_shuttle.db`; deleting that file resets the sample data the next time the API starts.

## Git and the friend's GitHub repository

This is an editable copy made from the ZIP, so it does not contain the friend's Git history or remote connection. Do not push this folder as a new repository if your goal is to finish your friend's existing project.

1. Ask your friend to add your GitHub username as a collaborator if you need to push changes.
2. In GitHub Desktop, choose **File → Clone repository**, paste the repository link your friend sent, and choose where to save it.
3. Copy the project changes from this project folder into that cloned repository. Keep `.git` intact and do not copy `node_modules`, `.venv`, or generated database files.
4. In GitHub Desktop, review the changed-file list. Enter a short summary such as `Add study progress project`, then choose **Commit to the current branch**.
5. Choose **Push origin** to upload your commit. If GitHub reports that you do not have access, ask your friend to grant collaborator access. Avoid force-pushing.

Ask me before you copy changes over if you want help identifying exactly which files to copy into the cloned repository.


