import { useCallback, useEffect, useState } from 'react';
import API from './services/api';
import './App.css';

const sections = ['Overview', 'My subjects', 'Tasks', 'Study sessions', 'Difficulties', 'Stress & wellbeing', 'Progress', 'My profile'];

function scoreRemark(percentage) {
  if (percentage >= 80) return 'Excellent work â€” keep it up!';
  if (percentage >= 60) return 'Good progress â€” keep practicing!';
  if (percentage >= 40) return 'You are improving â€” keep going!';
  return 'Keep going. Review the basics and ask for help if needed.';
}

function savedUser() {
  try {
    const parsed = JSON.parse(sessionStorage.getItem('studyShuttleUser') || 'null');
    if (parsed?.token) return parsed;
  } catch {
    sessionStorage.removeItem('studyShuttleUser');
  }
  return null;
}

function App() {
  const [section, setSection] = useState('Overview');
  const [user, setUser] = useState(savedUser);
  const [registering, setRegistering] = useState(false);
  const [loginForm, setLoginForm] = useState({ username: 'user1', password: 'user1@12345' });
  const [registration, setRegistration] = useState({ name: '', email: '', username: '', program: '', semester: 1, password: '' });
  const [loginError, setLoginError] = useState('');
  const [data, setData] = useState({ profile: {}, dashboard: { recent: [] }, tasks: [], sessions: [], subjects: [], enrollments: [], difficulties: [], stress: [], performance: [], insights: { subject_averages: [], study_totals: [], pending_tasks: [] } });
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [task, setTask] = useState({ subject_id: '', task_name: '', deadline: '', priority: 'Medium' });
  const [session, setSession] = useState({ subject_id: '', session_date: new Date().toISOString().slice(0, 10), duration_minutes: 45, productivity: 4, notes: '' });
  const [difficulty, setDifficulty] = useState({ session_id: '', difficulty_type: 'Focus', description: '', severity: 'Medium' });
  const [stress, setStress] = useState({ session_id: '', stress_level: 4, reason: '', notes: '' });
  const [score, setScore] = useState({ subject_id: '', assessment_name: '', marks_obtained: '', max_marks: 100, assessment_date: new Date().toISOString().slice(0, 10) });
  const [profileForm, setProfileForm] = useState({ name: '', program: '', semester: 1 });
  const [subjectForm, setSubjectForm] = useState({ subject_name: '', subject_code: '', difficulty_level: 'Medium' });

  const load = useCallback(async () => {
    try {
      const routes = ['me', 'dashboard', 'tasks', 'sessions', 'subjects', 'enrollments', 'difficulties', 'stress', 'performance', 'insights'];
      const responses = await Promise.all(routes.map(route => API.get('/api/' + route)));
      const [profile, dashboard, tasks, sessions, subjects, enrollments, difficulties, stressRows, performance, insights] = responses.map(response => response.data);
      setData({ profile, dashboard, tasks, sessions, subjects, enrollments, difficulties, stress: stressRows, performance, insights });
      setProfileForm({ name: profile.name, program: profile.program, semester: profile.semester });
      setTask(current => ({ ...current, subject_id: enrollments.some(item => item.subject_id === current.subject_id) ? current.subject_id : (enrollments[0]?.subject_id ?? '') }));
      setSession(current => ({ ...current, subject_id: enrollments.some(item => item.subject_id === current.subject_id) ? current.subject_id : (enrollments[0]?.subject_id ?? '') }));
      setDifficulty(current => ({ ...current, session_id: sessions.some(item => item.session_id === Number(current.session_id)) ? Number(current.session_id) : (sessions[0]?.session_id ?? '') }));
      setScore(current => ({ ...current, subject_id: enrollments.some(item => item.subject_id === Number(current.subject_id)) ? Number(current.subject_id) : (enrollments[0]?.subject_id ?? '') }));
      setError('');
      return true;
    } catch (e) {
      if (e.response?.status === 401) {
        sessionStorage.removeItem('studyShuttleUser');
        setUser(null);
        setError('Your sign-in expired. Please sign in again.');
      } else {
        setError('Could not load your records. Check that the backend is running, then refresh.');
      }
      return false;
    }
  }, []);

  useEffect(() => { if (user) load(); }, [user, load]);

  async function signIn(e) {
    e.preventDefault();
    setLoginError('');
    try {
      const response = await API.post('/api/login', loginForm);
      sessionStorage.setItem('studyShuttleUser', JSON.stringify(response.data));
      setUser(response.data);
      setSection('Overview');
    } catch (err) {
      setLoginError(err.response?.data?.detail || 'Sign-in failed. Check your username and password.');
    }
  }

  async function register(e) {
    e.preventDefault();
    setLoginError('');
    try {
      const response = await API.post('/api/register', registration);
      sessionStorage.setItem('studyShuttleUser', JSON.stringify(response.data));
      setUser(response.data);
      setSection('Overview');
    } catch (err) {
      setLoginError(err.response?.data?.detail || 'Registration failed. Check the information and try again.');
    }
  }

  async function signOut() {

    try { await API.post('/api/logout'); } catch { /* Clear local sign-in even if the server is unavailable. */ }
    sessionStorage.removeItem('studyShuttleUser');
    setUser(null);
    setSection('Overview');
    setData({ profile: {}, dashboard: { recent: [] }, tasks: [], sessions: [], subjects: [], enrollments: [], difficulties: [], stress: [], performance: [], insights: { subject_averages: [], study_totals: [], pending_tasks: [] } });
  }

  async function action(request, message) {
    setError('');
    try {
      await request();
      if (!await load()) return false;
      setNotice(message);
      setTimeout(() => setNotice(''), 3000);
      return true;
    } catch (err) {
      if (err.response?.status === 401) {
        sessionStorage.removeItem('studyShuttleUser');
        setUser(null);
      }
      setError(err.response?.data?.detail || 'That action did not work. Check your entries and try again.');
      return false;
    }
  }

  async function submitTask(e) {
    e.preventDefault();
    if (!task.subject_id) { setError('Enroll in a subject before creating a task.'); return; }
    if (await action(() => API.post('/api/tasks', task), 'Task created successfully')) {
      setTask(current => ({ ...current, task_name: '', deadline: '' }));
    }
  }

  async function submitSession(e) {
    e.preventDefault();
    if (!session.subject_id) { setError('Enroll in a subject before recording a session.'); return; }
    if (await action(() => API.post('/api/sessions', session), 'Study session saved')) {
      setSession(current => ({ ...current, notes: '' }));
    }
  }

  async function submitDifficulty(e) {
    e.preventDefault();
    if (await action(() => API.post('/api/difficulties', difficulty), 'Difficulty report saved')) {
      setDifficulty(current => ({ ...current, description: '' }));
    }
  }

  async function submitStress(e) {
    e.preventDefault();
    const body = { ...stress, session_id: stress.session_id ? Number(stress.session_id) : null };
    if (await action(() => API.post('/api/stress', body), 'Stress check-in saved')) {
      setStress(current => ({ ...current, reason: '', notes: '' }));
    }
  }

  async function submitScore(e) {
    e.preventDefault();
    if (!score.subject_id) { setError('Enroll in a subject before adding a score.'); return; }
    const body = { ...score, subject_id: Number(score.subject_id), marks_obtained: Number(score.marks_obtained), max_marks: Number(score.max_marks) };
    if (await action(() => API.post('/api/performance', body), 'Assessment score saved')) {
      setScore(current => ({ ...current, assessment_name: '', marks_obtained: '' }));
    }
  }

  async function submitSubject(e) {
    e.preventDefault();
    if (await action(() => API.post('/api/subjects', subjectForm), 'Subject added to the catalogue and enrolled for you')) {
      setSubjectForm({ subject_name: '', subject_code: '', difficulty_level: 'Medium' });
    }
  }

  async function submitProfile(e) {
    e.preventDefault();
    if (await action(() => API.put('/api/me', profileForm), 'Profile updated')) {
      const updated = { ...user, name: profileForm.name };
      sessionStorage.setItem('studyShuttleUser', JSON.stringify(updated));
      setUser(updated);
    }
  }

  const enrolledOptions = data.enrollments.map(subject => (
    <option key={subject.subject_id} value={subject.subject_id}>{subject.subject_name}</option>
  ));

  if (!user) {
    return <div className="login-screen">
      <section className="login-card">
        <div className="login-brand"><span className="brand-mark">SS</span><div><b>Study Shuttle</b><small>Student study progress</small></div></div>
        <span className="eyebrow">{registering ? 'CREATE YOUR ACCOUNT' : 'STUDENT SIGN IN'}</span>
        <h1>{registering ? 'Join Study Shuttle' : 'Sign in to your account'}</h1>
        <p className="login-copy">{registering ? 'Create a student profile to manage your own study activity.' : 'Track your subjects, tasks, sessions, and progress.'}</p>
        {registering ? <form className="login-form" onSubmit={register}>
          <label>Full name<input required minLength="2" maxLength="100" value={registration.name} onChange={e => setRegistration({ ...registration, name: e.target.value })} /></label>
          <label>Email<input type="email" required value={registration.email} onChange={e => setRegistration({ ...registration, email: e.target.value })} /></label>
          <label>Username<input required minLength="3" maxLength="30" value={registration.username} onChange={e => setRegistration({ ...registration, username: e.target.value })} /></label>
          <label>Program<input required minLength="2" value={registration.program} onChange={e => setRegistration({ ...registration, program: e.target.value })} /></label>
          <label>Semester<input type="number" min="1" max="12" required value={registration.semester} onChange={e => setRegistration({ ...registration, semester: Number(e.target.value) })} /></label>

          <label>Password<input type="password" minLength="6" required value={registration.password} onChange={e => setRegistration({ ...registration, password: e.target.value })} /></label>
          {loginError && <div className="alert">{loginError}</div>}
          <button className="primary">Create student account</button>
        </form> : <form className="login-form" onSubmit={signIn}>
          <label>Username or email<input required value={loginForm.username} onChange={e => setLoginForm({ ...loginForm, username: e.target.value })} /></label>
          <label>Password<input type="password" required value={loginForm.password} onChange={e => setLoginForm({ ...loginForm, password: e.target.value })} /></label>
          {loginError && <div className="alert">{loginError}</div>}
          <button className="primary">Sign in</button>
        </form>}
        {!registering && <div className="account-note"><b>Demo student account</b><span>Username: user1</span><span>Password: user1@12345</span><small>Other sample student accounts use username student2 and password study123.</small></div>}
        <button className="text-btn auth-toggle" onClick={() => { setRegistering(!registering); setLoginError(''); }}>{registering ? 'Already registered? Sign in' : 'New student? Create an account'}</button>
        <p className="login-footnote">Fictional student data for a local classroom demonstration.</p>
      </section>
    </div>;
  }

  return <div className="app-shell">
    <aside className="sidebar">
      <div className="brand"><span className="brand-mark">SS</span><div><b>Study Shuttle</b><small>Student study progress</small></div></div>
      <div className="nav-label">MY WORKSPACE</div>
      <nav>{sections.map((item, index) => (
        <button key={item} className={section === item ? 'nav-item active' : 'nav-item'} onClick={() => setSection(item)}>
          <span>{String(index + 1).padStart(2, '0')}</span>{item}
        </button>
      ))}</nav>
      <div className="side-note"><b>My account</b><p>{data.profile.program || 'Student profile'} Â· Semester {data.profile.semester || 'â€”'}</p><span className="status-dot" /> Local database</div>
    </aside>

    <main className="main">
      <header className="topbar"><div><span className="crumb">STUDENT WORKSPACE</span><h1>{section}</h1></div>
        <div className="top-actions"><span className="welcome-user">Hello, {user.name}</span><button className="refresh" onClick={load}>Refresh</button><button className="refresh" onClick={signOut}>Sign out</button></div>
      </header>
      {error && <div className="alert">{error}</div>}{notice && <div className="notice">{notice}</div>}

      {section === 'Overview' && <>
        <p className="intro">A personal view of your study plan and progress.</p>
        <div className="stats">
          {[
            ['Enrolled subjects', data.dashboard.subjects],
            ['My tasks', data.dashboard.tasks],
            ['Tasks to complete', data.dashboard.pending],
            ['Study sessions', data.dashboard.sessions],
            ['Open difficulties', data.dashboard.open_difficulties],
          ].map(([label, value]) => <div className="stat" key={label}><span>{label}</span><b>{value ?? 'â€”'}</b><small>Your records</small></div>)}
        </div>
        <section className="panel"><div className="panel-head"><div><span className="eyebrow">RECENT ACTIVITY</span><h2>My recent study sessions</h2></div><button className="text-btn" onClick={() => setSection('Study sessions')}>View sessions</button></div>
          {data.dashboard.recent.length ? <div className="table-wrap"><table><thead><tr><th>Subject</th><th>Date</th><th>Duration</th><th>Productivity</th></tr></thead><tbody>{data.dashboard.recent.map((item, index) => <tr key={index}><td>{item.subject}</td><td>{item.session_date}</td><td>{item.duration_minutes} min</td><td>{item.productivity}/5</td></tr>)}</tbody></table></div> : <p className="empty-state">No study sessions yet. Enroll in a subject and log your first session.</p>}
        </section>
      </>}

      {section === 'My subjects' && <>
        <p className="intro">Add a subject to the catalogue or enroll in one that is already listed.</p>
        <section className="panel form-panel"><div className="panel-head"><div><span className="eyebrow">NEW SUBJECT</span><h2>Add a subject</h2></div></div>
          <form className="form-grid" onSubmit={submitSubject}>
            <label>Subject name<input required minLength="2" maxLength="100" placeholder="e.g. Operating Systems" value={subjectForm.subject_name} onChange={e => setSubjectForm({ ...subjectForm, subject_name: e.target.value })} /></label>
            <label>Subject code<input required minLength="2" maxLength="20" pattern="[A-Za-z0-9_-]+" title="Use letters, numbers, hyphens, or underscores" placeholder="e.g. OS204" value={subjectForm.subject_code} onChange={e => setSubjectForm({ ...subjectForm, subject_code: e.target.value })} /></label>
            <label>Difficulty<select value={subjectForm.difficulty_level} onChange={e => setSubjectForm({ ...subjectForm, difficulty_level: e.target.value })}>{['Easy', 'Medium', 'Hard'].map(value => <option key={value}>{value}</option>)}</select></label>
            <button className="primary form-submit">Add subject</button>
          </form>
        </section>

        {data.subjects.length ? <div className="subject-grid">{data.subjects.map(subject => <article className="subject-card" key={subject.subject_id}>
          <span className="subject-code">{subject.subject_code}</span><h3>{subject.subject_name}</h3><p>Difficulty: {subject.difficulty_level}</p>
          {subject.is_enrolled ? <span className="enrolled-label">Enrolled</span> : <button className="primary subject-action" onClick={() => action(() => API.post('/api/enrollments', { subject_id: subject.subject_id }), 'Subject enrollment saved')}>Enroll in subject</button>}
        </article>)}</div> : <section className="panel"><p className="empty-state">No subjects are available.</p></section>}
        {data.enrollments.length > 0 && <section className="panel"><div className="panel-head"><div><span className="eyebrow">MY SUBJECTS</span><h2>Enrolled subjects ({data.enrollments.length})</h2></div></div><p>{data.enrollments.map(item => item.subject_name).join(' Â· ')}</p></section>}
      </>}

      {section === 'Tasks' && <>
        <p className="intro">Create your own tasks, update their status, and remove tasks you no longer need.</p>
        {!data.enrollments.length && <div className="alert">Enroll in at least one subject before creating a task. <button className="text-btn" onClick={() => setSection('My subjects')}>Browse subjects</button></div>}
        <section className="panel form-panel"><div className="panel-head"><div><span className="eyebrow">NEW TASK</span><h2>Create a study task</h2></div></div>
          <form className="form-grid" onSubmit={submitTask}>
            <label>Task name<input required minLength="2" maxLength="160" placeholder="e.g. Revise SQL joins" value={task.task_name} onChange={e => setTask({ ...task, task_name: e.target.value })} /></label>
            <label>Subject<select required disabled={!data.enrollments.length} value={task.subject_id} onChange={e => setTask({ ...task, subject_id: Number(e.target.value) })}>{enrolledOptions}</select></label>
            <label>Deadline<input type="date" value={task.deadline} onChange={e => setTask({ ...task, deadline: e.target.value })} /></label>
            <label>Priority<select value={task.priority} onChange={e => setTask({ ...task, priority: e.target.value })}>{['High', 'Medium', 'Low'].map(value => <option key={value}>{value}</option>)}</select></label>
            <button className="primary form-submit" disabled={!data.enrollments.length}>Add task</button>
          </form>
        </section>
        <section className="panel"><div className="panel-head"><div><span className="eyebrow">MY TASKS</span><h2>Tasks ({data.tasks.length})</h2></div></div>
          {data.tasks.length ? <div className="table-wrap"><table><thead><tr><th>Task</th><th>Subject</th><th>Deadline</th><th>Priority</th><th>Status</th><th>Action</th></tr></thead><tbody>{data.tasks.map(item => <tr key={item.task_id}>
            <td>{item.task_name}</td><td>{item.subject}</td><td>{item.deadline || 'â€”'}</td><td><span className={'badge ' + item.priority.toLowerCase()}>{item.priority}</span></td>
            <td><select className="inline-select" value={item.status} onChange={e => action(() => API.patch('/api/tasks/' + item.task_id, { status: e.target.value }), 'Task status updated')}><option>Pending</option><option>In Progress</option><option>Completed</option></select></td>
            <td><button className="delete-btn" onClick={() => window.confirm('Delete this task?') && action(() => API.delete('/api/tasks/' + item.task_id), 'Task deleted')}>Delete</button></td>
          </tr>)}</tbody></table></div> : <p className="empty-state">No tasks yet. Create your first study task above.</p>}
        </section>
      </>}

      {section === 'Study sessions' && <>
        <p className="intro">Record your study time and review your session history.</p>
        {!data.enrollments.length && <div className="alert">Enroll in a subject before recording a session. <button className="text-btn" onClick={() => setSection('My subjects')}>Browse subjects</button></div>}
        <section className="panel form-panel"><div className="panel-head"><div><span className="eyebrow">NEW SESSION</span><h2>Log a study session</h2></div></div>
          <form className="form-grid" onSubmit={submitSession}>

            <label>Subject<select required disabled={!data.enrollments.length} value={session.subject_id} onChange={e => setSession({ ...session, subject_id: Number(e.target.value) })}>{enrolledOptions}</select></label>
            <label>Date<input type="date" required value={session.session_date} onChange={e => setSession({ ...session, session_date: e.target.value })} /></label>
            <label>Duration (minutes)<input type="number" min="1" max="1440" required value={session.duration_minutes} onChange={e => setSession({ ...session, duration_minutes: Number(e.target.value) })} /></label>
            <label>Productivity (1â€“5)<select value={session.productivity} onChange={e => setSession({ ...session, productivity: Number(e.target.value) })}>{[1, 2, 3, 4, 5].map(value => <option key={value}>{value}</option>)}</select></label>
            <label>Notes<input maxLength="500" value={session.notes} onChange={e => setSession({ ...session, notes: e.target.value })} placeholder="What did you study?" /></label>
            <button className="primary form-submit" disabled={!data.enrollments.length}>Save session</button>
          </form>
        </section>
        <section className="panel"><div className="panel-head"><div><span className="eyebrow">MY ACTIVITY</span><h2>Study sessions ({data.sessions.length})</h2></div></div>
          {data.sessions.length ? <div className="table-wrap"><table><thead><tr><th>Subject</th><th>Date</th><th>Duration</th><th>Productivity</th><th>Notes</th></tr></thead><tbody>{data.sessions.map(item => <tr key={item.session_id}><td>{item.subject}</td><td>{item.session_date}</td><td>{item.duration_minutes} min</td><td>{item.productivity}/5</td><td>{item.notes || 'â€”'}</td></tr>)}</tbody></table></div> : <p className="empty-state">No sessions yet. Log your first session above.</p>}
        </section>
      </>}

      {section === 'Difficulties' && <>
        <p className="intro">Use this for a specific obstacle during a session, such as a confusing topic or difficulty focusing. For overall pressure or workload, use Stress &amp; wellbeing.</p>
        {!data.sessions.length && <div className="alert">Log a study session before reporting a difficulty. <button className="text-btn" onClick={() => setSection('Study sessions')}>Go to sessions</button></div>}
        <section className="panel form-panel"><div className="panel-head"><div><span className="eyebrow">NEW RECORD</span><h2>Report a study difficulty</h2></div></div>
          <form className="form-grid" onSubmit={submitDifficulty}>
            <label>Study session<select required disabled={!data.sessions.length} value={difficulty.session_id} onChange={e => setDifficulty({ ...difficulty, session_id: Number(e.target.value) })}>{!data.sessions.length && <option value="">Log a session first</option>}{data.sessions.map(item => <option key={item.session_id} value={item.session_id}>{item.subject} Â· {item.session_date}</option>)}</select></label>
            <label>Difficulty type<select value={difficulty.difficulty_type} onChange={e => setDifficulty({ ...difficulty, difficulty_type: e.target.value })}>{['Focus', 'Concept understanding', 'Time management', 'Distraction', 'Other'].map(value => <option key={value}>{value}</option>)}</select></label>
            <label>Severity<select value={difficulty.severity} onChange={e => setDifficulty({ ...difficulty, severity: e.target.value })}>{['Low', 'Medium', 'High'].map(value => <option key={value}>{value}</option>)}</select></label>
            <label>Description<input required minLength="3" maxLength="500" placeholder="e.g. I found INNER JOIN confusing" value={difficulty.description} onChange={e => setDifficulty({ ...difficulty, description: e.target.value })} /></label>
            <button className="primary form-submit" disabled={!data.sessions.length}>Save difficulty</button>
          </form>
        </section>
        <section className="panel"><div className="panel-head"><div><span className="eyebrow">MY DIFFICULTIES</span><h2>Study challenges ({data.difficulties.length})</h2></div></div>

          {data.difficulties.length ? <div className="table-wrap"><table><thead><tr><th>Type</th><th>Subject</th><th>Description</th><th>Severity</th><th>Status</th><th>Action</th></tr></thead><tbody>{data.difficulties.map(item => <tr key={item.difficulty_id}><td>{item.difficulty_type}</td><td>{item.subject}</td><td>{item.description}</td><td>{item.severity}</td><td>{item.solved ? 'Resolved' : 'Open'}</td><td>{!item.solved && <button className="text-btn" onClick={() => action(() => API.patch('/api/difficulties/' + item.difficulty_id, { solved: true }), 'Difficulty marked resolved')}>Mark resolved</button>}</td></tr>)}</tbody></table></div> : <p className="empty-state">No difficulties have been recorded.</p>}
        </section>
      </>}

      {section === 'Stress & wellbeing' && <>
        <p className="intro">Use this for how pressured or overloaded you felt overall, such as stress about exams or deadlines. A specific study obstacle belongs under Difficulties. This is not a health assessment.</p>
        <section className="panel form-panel"><div className="panel-head"><div><span className="eyebrow">STUDENT CHECK-IN</span><h2>Record a stress check-in</h2></div></div>
          <form className="form-grid" onSubmit={submitStress}>
            <label>Stress level (1â€“10)<input type="number" min="1" max="10" required value={stress.stress_level} onChange={e => setStress({ ...stress, stress_level: Number(e.target.value) })} /></label>
            <label>Reason<input required minLength="2" maxLength="200" placeholder="e.g. Course workload" value={stress.reason} onChange={e => setStress({ ...stress, reason: e.target.value })} /></label>
            <label>Related session (optional)<select value={stress.session_id} onChange={e => setStress({ ...stress, session_id: e.target.value })}><option value="">No linked session</option>{data.sessions.map(item => <option key={item.session_id} value={item.session_id}>{item.subject} Â· {item.session_date}</option>)}</select></label>
            <label>Notes<input maxLength="500" value={stress.notes} onChange={e => setStress({ ...stress, notes: e.target.value })} placeholder="Optional note" /></label>
            <button className="primary form-submit">Save check-in</button>
          </form>
        </section>
        <section className="panel"><div className="panel-head"><div><span className="eyebrow">MY CHECK-INS</span><h2>Stress history ({data.stress.length})</h2></div></div>
          {data.stress.length ? <div className="table-wrap"><table><thead><tr><th>Date</th><th>Level</th><th>Reason</th><th>Related session</th><th>Notes</th></tr></thead><tbody>{data.stress.map(item => <tr key={item.stress_id}><td>{item.recorded_date}</td><td>{item.stress_level}/10</td><td>{item.reason}</td><td>{item.session_date || 'â€”'}</td><td>{item.notes || 'â€”'}</td></tr>)}</tbody></table></div> : <p className="empty-state">No check-ins yet. Add one above if you want to track study stress.</p>}
        </section>
      </>}

      {section === 'Progress' && <>
        <p className="intro">Your study and assessment summaries are calculated from your own saved records.</p>
        {!data.enrollments.length && <div className="alert">Enroll in a subject before adding a score. <button className="text-btn" onClick={() => setSection('My subjects')}>Browse subjects</button></div>}
        <section className="panel form-panel"><div className="panel-head"><div><span className="eyebrow">NEW ASSESSMENT</span><h2>Add a score</h2></div></div>
          <form className="form-grid" onSubmit={submitScore}>
            <label>Subject<select required disabled={!data.enrollments.length} value={score.subject_id} onChange={e => setScore({ ...score, subject_id: Number(e.target.value) })}>{enrolledOptions}</select></label>
            <label>Assessment name<input required minLength="2" maxLength="120" placeholder="e.g. Unit test 2" value={score.assessment_name} onChange={e => setScore({ ...score, assessment_name: e.target.value })} /></label>
            <label>Marks obtained<input type="number" min="0" step="any" required value={score.marks_obtained} onChange={e => setScore({ ...score, marks_obtained: e.target.value })} /></label>
            <label>Maximum marks<input type="number" min="1" step="any" required value={score.max_marks} onChange={e => setScore({ ...score, max_marks: e.target.value })} /></label>
            <label>Assessment date<input type="date" required value={score.assessment_date} onChange={e => setScore({ ...score, assessment_date: e.target.value })} /></label>
            <button className="primary form-submit" disabled={!data.enrollments.length}>Save score</button>
          </form>
        </section>
        <div className="query-grid">
          {[
            ['Average score by subject', data.insights.subject_averages, ['subject', 'average_percent', 'assessments']],
            ['Study time by subject', data.insights.study_totals, ['subject', 'minutes', 'avg_productivity']],
            ['Tasks to focus on', data.insights.pending_tasks, ['task_name', 'subject', 'priority', 'deadline']],
          ].map(([title, records, columns]) => <section className="panel" key={title}><div className="panel-head"><div><span className="eyebrow">MY PROGRESS</span><h2>{title}</h2></div></div>
            {records.length ? <div className="table-wrap"><table><thead><tr>{columns.map(column => <th key={column}>{column.replaceAll('_', ' ')}</th>)}</tr></thead><tbody>{records.map((record, index) => <tr key={index}>{columns.map(column => <td key={column}>{column === 'minutes' ? record[column] + ' min' : column === 'average_percent' ? record[column] + '%' : record[column]}</td>)}</tr>)}</tbody></table></div> : <p className="empty-state">No matching records yet.</p>}
            <p className="result-count">{records.length} rows returned</p>
          </section>)}
        </div>

        <section className="panel"><div className="panel-head"><div><span className="eyebrow">ASSESSMENTS</span><h2>My performance ({data.performance.length})</h2></div></div>
          {data.performance.length ? <div className="table-wrap"><table><thead><tr><th>Subject</th><th>Assessment</th><th>Marks</th><th>Score</th><th>Remark</th><th>Date</th></tr></thead><tbody>{data.performance.map(item => <tr key={item.performance_id}><td>{item.subject}</td><td>{item.assessment_name}</td><td>{item.marks_obtained}/{item.max_marks}</td><td>{item.percentage}%</td><td>{scoreRemark(item.percentage)}</td><td>{item.assessment_date}</td></tr>)}</tbody></table></div> : <p className="empty-state">Assessment results have not been added for this account yet.</p>}
        </section>
      </>}

      {section === 'My profile' && <>
        <p className="intro">Your account is linked to your own student record.</p>
        <section className="panel form-panel"><div className="panel-head"><div><span className="eyebrow">STUDENT PROFILE</span><h2>Update my details</h2></div></div>
          <p className="intro">Sign-in username: <b>{data.profile.username}</b> Â· Email: <b>{data.profile.email}</b></p>
          <form className="form-grid" onSubmit={submitProfile}>
            <label>Full name<input required minLength="2" maxLength="100" value={profileForm.name} onChange={e => setProfileForm({ ...profileForm, name: e.target.value })} /></label>
            <label>Program<input required minLength="2" maxLength="100" value={profileForm.program} onChange={e => setProfileForm({ ...profileForm, program: e.target.value })} /></label>
            <label>Semester<input type="number" min="1" max="12" required value={profileForm.semester} onChange={e => setProfileForm({ ...profileForm, semester: Number(e.target.value) })} /></label>
            <button className="primary form-submit">Save profile</button>
          </form>
        </section>
      </>}

      <footer>Study Shuttle System <span>â€¢</span> Fictional student data for classroom demonstration</footer>
    </main>
  </div>;
}

export default App;
