# AGENTS.md

## Repo Shape

- This is not an npm workspace: install root and frontend dependencies separately with `npm install` and `npm install --prefix frontend`.
- Root `package.json` is only the Tauri CLI wrapper; React/Vite scripts and dependencies live in `frontend/package.json`.
- `frontend/` is the React + TypeScript + Vite UI; entrypoint is `frontend/src/main.tsx`, app state is currently in `frontend/src/App.tsx`.
- `backend/` is a minimal Flask mock API; keep future AI/backend work behind this boundary instead of calling providers from React.
- `src-tauri/` is Tauri v2 shell config and Rust entrypoint; `src-tauri/tauri.conf.json` runs frontend commands from the repo root, so its npm prefixes are `frontend`, not `../frontend`.

## Development Commands

- Install JS deps: `npm install` then `npm install --prefix frontend`.
- Install Python deps: `python -m venv backend/.venv` then `backend/.venv/bin/pip install -r backend/requirements.txt`.
- Start Flask before using chat in the app: `backend/.venv/bin/python backend/app.py`.
- Start desktop dev app in another terminal: `npm run dev`; Tauri starts Vite but does not start Flask.
- Frontend build/typecheck: `npm run build --prefix frontend`.
- Full desktop production build: `npm run build` or `npm run tauri -- build`.

## API And Runtime Gotchas

- Frontend API base defaults to `http://127.0.0.1:5000`; override with `VITE_API_BASE_URL` if needed.
- Vite is pinned to `127.0.0.1:5173` with `strictPort: true`; a busy port fails dev startup instead of choosing another port.
- `npm run dev` / `npm run tauri -- dev` are long-running desktop dev commands; reaching `Running target/debug/cowriter` means launch succeeded.
- Flask endpoints currently verified by `GET /api/health` and `POST /api/chat` with `{ "message": "Hello" }`.

## Provider Integration Boundary

- Provider objects under `backend/auth/providers/` only communicate with and validate external provider APIs. They must not import database models, query or mutate the database, use database sessions, or persist credentials.
- Flask API routes own all provider-connection persistence, including database records and credential/keyring storage.
- Provider objects return the normalized connection information the API needs to persist; they never persist that information themselves.

## Current Limits

- There are no lint, formatter, unit test, or CI configs yet; do not invent commands beyond the package scripts.
- Chat/project persistence is in React session state only; mock projects live in `frontend/src/data/mockProjects.ts`.
- `/api/chat` returns a deterministic placeholder; do not add OpenAI, Anthropic, LangChain, LangGraph, MCP, RAG, embeddings, local models, auth, or database code unless explicitly requested.
- Build outputs and generated Tauri files are ignored: `frontend/dist/`, `src-tauri/target/`, and `src-tauri/gen/`.
