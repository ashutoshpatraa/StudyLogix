# StudyLogix context

## Project summary
StudyLogix is a Flask-based study tracker and productivity dashboard. It helps users log study sessions, set daily and weekly goals, run a Pomodoro timer, review analytics, and connect with friends in a social learning workflow.

The app is designed around a polished glassmorphism UI and emphasizes a calm focus experience inspired by Nothing OS styling. Most of the project is server-rendered HTML using Jinja2 templates with a small set of JSON APIs for timer actions.

## Stack and runtime
- Python 3.8+
- Flask 3.x
- SQLite database (`study_tracker.db` by default)
- bcrypt for password hashing
- Flask-WTF for CSRF protection
- Bootstrap 5, Chart.js, Font Awesome, custom CSS/JS
- Gunicorn for production serving

## Primary files
- `app.py`: main Flask application, route definitions, validation helpers, security headers, session logic
- `database.py`: SQLite schema creation and database manager
- `services/`: feature-specific service modules such as user/session/friend/pomodoro managers
- `templates/`: HTML pages for landing, auth, dashboard, analytics, groups, friends, timer, etc.
- `static/`: CSS, JS, images, and front-end assets
- `tests/`: auth and study-flow smoke tests
- `render.yaml`: deployment configuration for Render

## Core product behavior
- User registration and login with secure password hashing
- Study session logging with subject, duration, mood, productivity, notes
- Daily and weekly goal tracking
- Pomodoro timer lifecycle: start, active tracking, completion, cancellation
- Friend requests and progress tracking
- Analytics dashboard for trends and subject totals
- Sessions view for study history and summaries

## Important app patterns
- `app.py` owns validation helpers such as username, password, subject, duration, and notes checks.
- `login_required` redirects unauthenticated users to `/login`.
- `api_login_required` returns a JSON 401 for API requests.
- Security headers are injected globally in `set_security_headers()`.
- The app reads `SECRET_KEY` from environment variables. In local dev it falls back to random bytes, but production should always set a stable secret.
- The database is created automatically on first run through the database manager.

## Local development workflow
1. Create a venv and activate it.
2. Install dependencies: `pip install -r requirements.txt`
3. Copy environment variables: `cp .env.example .env`
4. Set a strong `SECRET_KEY` value in `.env`
5. Run the app: `python app.py`
6. Open `http://localhost:5000`

## Testing workflow
- Use pytest for validation.
- The project includes auth tests and study-flow tests.
- Test setup often creates an in-memory SQLite DB and uses `app.test_client()`.

Recommended command:
- `pytest`

## Deployment notes
- Render deployment is configured via `render.yaml`.
- Production should use a persistent disk for SQLite because file-based state will otherwise be lost between deploys.
- For production, set `FLASK_ENV=production` and a valid `SECRET_KEY`.

## Working conventions for future changes
- Prefer surgical changes that preserve existing route names and DB schema expectations.
- Keep frontend and backend behavior aligned when editing templates or APIs.
- Update or add tests whenever altering auth, timers, study logs, or analytics logic.
- Keep security-conscious defaults: validate user input, maintain session checks, and avoid exposing sensitive details in responses.
