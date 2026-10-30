# Claude instructions for StudyLogix

## Role
Act as a careful Python/Flask engineer working in this repository. Prefer small, correct changes that align with the app's current architecture and styling.

## Project-specific guidance
- Treat StudyLogix as a Flask study productivity app centered on user sessions, goals, Pomodoro workflows, and analytics.
- Preserve the existing SQLite-first design unless the task explicitly requires a bigger architecture change.
- Keep routes, templates, and service-layer wiring compatible with the current app structure.
- Use `app.py` as the main route and validation reference point before making behavior changes.
- Prefer targeted updates in `database.py` and the service modules when behavior changes require data access or session logic.

## Workflow
1. Inspect the relevant route, manager, or database code before editing.
2. Make precise changes with minimal scope.
3. Validate with the smallest relevant pytest command.
4. Keep any user-visible messaging consistent with the existing app tone.

## Quality bar
- Do not change the application's core UX or security model without clear justification.
- Preserve session security, authentication checks, and input validation patterns.
- Keep tests passing and add/adjust tests when behavior changes are significant.
- Favor clean, readable Python over clever or over-abstracted solutions.

## Validation commands
- `pytest`
- For narrower checks, run only the relevant test file or class when possible.

## Notes for AI agents
- The app is designed for local dev and Render deployment with environment-based config.
- When working on deployment or secret handling, ensure `SECRET_KEY` is managed explicitly.
- When touching the UI, maintain the current glassmorphism aesthetic unless a request specifically asks for a redesign.
