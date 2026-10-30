# StudyLogix memory

## Core memory
- Repository: `StudyLogix`
- Type: Python Flask web app for study tracking and focus management
- Persistence: SQLite file database with automatic table creation
- Primary entry point: `app.py`
- Supporting database logic: `database.py`
- Feature modules live under `services/`

## Known working patterns
- Use `DatabaseManager(':memory:')` in tests to isolate state.
- Tests rely on `app.test_client()` and `WTF_CSRF_ENABLED = False` for form submissions.
- Authentication is enforced with `login_required` for server-rendered routes and `api_login_required` for JSON endpoints.
- Session state is tracked in Flask `session`, with `user_id` and `username` as key values.

## Important app behavior
- Registration validates username and password before creating the user.
- Login uses bcrypt-based password checks.
- Daily goals and study sessions are stored in SQLite with user ownership enforceable via the DB schema.
- Pomodoro sessions have an explicit active/completed/cancelled lifecycle.
- Security headers are set globally after each response using the `after_request` hook.

## Common commands
- Install dependencies: `pip install -r requirements.txt`
- Start app: `python app.py`
- Run tests: `pytest`
- Set environment: `cp .env.example .env` and configure `SECRET_KEY`

## Things to preserve when editing
- Keep the project's route names and templates consistent.
- Preserve SQLite compatibility and avoid assuming a larger relational DB.
- Keep user authentication and session access checks intact.
- Update targeted tests whenever modifying auth, goals, timer logic, or analytics behavior.

## Current design direction
The project is intentionally a polished, single-server app with lightweight state and minimal operational complexity. Prefer small, layered improvements over broad rewrites.
