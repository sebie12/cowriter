# AGENTS.md

## Repo Shape

- This is not an npm workspace: install root and frontend dependencies separately with `npm install` and `npm install --prefix frontend`.
- Root `package.json` is only the Tauri CLI wrapper; React/Vite scripts and dependencies live in `frontend/package.json`.
- `frontend/` is the React + TypeScript + Vite UI; entrypoint is `frontend/src/main.tsx`, top-level app state is in `frontend/src/App.tsx`. All backend calls go through the injected `CowriterApi` in `frontend/src/services/backend/`.
- `backend/` is the Flask API: LLM providers, chat streaming, MCP project tools, and SQLite persistence. Keep AI/provider work behind this boundary instead of calling providers from React.
- `src-tauri/` is Tauri v2 shell config and Rust entrypoint. Project file listing and LaTeX source read/write are Rust commands in `src-tauri/src/main.rs`, called from `frontend/src/services/projectFilesystem.ts`.
- `src-tauri/tauri.conf.json` runs frontend commands from the repo root, so its npm prefixes are `frontend`, not `../frontend`.

## Development Commands

- Install JS deps: `npm install` then `npm install --prefix frontend`.
- Install Python deps: `python -m venv backend/.venv` then `backend/.venv/bin/pip install -r backend/requirements.txt`.
- Apply migrations: `backend/.venv/bin/flask --app backend.app db upgrade`. After model changes: `backend/.venv/bin/flask --app backend.app db migrate -m "..."`, review the file, then upgrade.
- Start Flask before using chat in the app: `backend/.venv/bin/python backend/app.py`.
- Start desktop dev app in another terminal: `npm run dev`; Tauri starts Vite but does not start Flask. `python run.py` starts Flask + Vite (no Tauri window).
- Backend tests (run from repo root): `backend/.venv/bin/python -m unittest discover -s backend/tests`; single module: `backend/.venv/bin/python -m unittest backend.tests.test_chat_route`.
- Frontend build/typecheck: `npm run build --prefix frontend`.
- Full desktop production build: `npm run build` or `npm run tauri -- build`.

## API And Runtime Gotchas

- Frontend API base defaults to `http://127.0.0.1:5000`; override with `VITE_API_BASE_URL` if needed. Never put backend secrets in `VITE_*` variables.
- Vite is pinned to `127.0.0.1:5173` with `strictPort: true`; a busy port fails dev startup instead of choosing another port.
- `npm run dev` / `npm run tauri -- dev` are long-running desktop dev commands; reaching `Running target/debug/cowriter` means launch succeeded.
- All backend routes use the `/api` prefix and imports use the `backend.` package prefix. The API contract is in `docs/frontend-backend-api.md`.
- `POST /api/chat` streams NDJSON events: `assistant_start` / `assistant_delta` / `assistant_end`, `tool_call`, then `done` or `error`.
- SQLite lives at `instance/database.db` by default; override with `COWRITER_DATABASE_URI`. `test_migrations.py` fails if models and migrations drift.

## Provider Integration Boundary

- Provider objects under `backend/auth/providers/` only communicate with and validate external provider APIs. They must not import database models, query or mutate the database, use database sessions, or persist credentials.
- Flask API routes own all provider-connection persistence, including database records and credential/keyring storage.
- Provider objects return the normalized connection information the API needs to persist; they never persist that information themselves.

## Current Limits

- There are no lint, formatter, frontend test, or CI configs yet; do not invent commands beyond the package scripts and the backend `unittest` suite.
- Projects and tool calls are persisted in the database; chat messages sent through `/api/chat` are not.
- Supported providers are OpenAI, Google Gemini, and Ollama. Do not add Anthropic, LangChain, LangGraph, RAG, or embeddings integrations unless explicitly requested.
