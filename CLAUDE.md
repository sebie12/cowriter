# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Cowriter is a desktop app for AI-assisted research and writing: React/Vite UI (`frontend/`), Tauri v2 shell (`src-tauri/`), and a Flask backend (`backend/`) that owns LLM providers, persistence, and MCP tool orchestration.

## Development rules

### Git workflow
- `dev` is the integration branch and runs alongside `main`. Never commit to or merge into `main` directly. Merges and pull requests to `main` are handled by the user.
- Every change gets its own branch created from `dev` (e.g. `feat/...`, `fix/...`, `refactor/...`), scoped to that one piece of work.
- When the work is done, merge the branch into `dev`.
- Commit messages should summarize what changed overall, not just name the files touched.

### Dependencies
- Ask the user before adding any new dependency (npm, Python, or Cargo).

## Commands

Not an npm workspace — root `package.json` only wraps the Tauri CLI; React deps/scripts live in `frontend/package.json`.

```bash
# Install
npm install && npm install --prefix frontend
python -m venv backend/.venv && backend/.venv/bin/pip install -r backend/requirements.txt

# Database (SQLite via Flask-Migrate; run from repo root)
backend/.venv/bin/flask --app backend.app db upgrade
backend/.venv/bin/flask --app backend.app db migrate -m "describe the change"   # after model changes; review the generated file

# Run
backend/.venv/bin/python backend/app.py   # Flask on 127.0.0.1:5000 (Tauri does NOT start it)
npm run dev                               # Tauri desktop app; starts Vite on 127.0.0.1:5173
python run.py                             # Flask + Vite together (browser only, no Tauri window)
# On Linux, WEBKIT_DISABLE_DMABUF_RENDERER=1 npm run tauri dev may be needed

# Build / typecheck
npm run build --prefix frontend           # tsc + vite build (the only frontend check)
npm run build                             # full Tauri production build

# Backend tests (unittest; run from repo root so `backend.*` imports resolve)
backend/.venv/bin/python -m unittest discover -s backend/tests
backend/.venv/bin/python -m unittest backend.tests.test_chat_route
backend/.venv/bin/python -m unittest backend.tests.test_chat_route.ChatRouteTests.test_passes_provider_independent_request_to_service
```

No linter, formatter, frontend tests, or CI are configured — don't invent commands. `test_migrations.py` runs `flask db upgrade` + `db check` against a temp DB, so it fails if models and migrations drift.

## Runtime gotchas

- Vite uses `strictPort: true` on 5173; a busy port fails startup.
- `src-tauri/tauri.conf.json` runs commands from repo root, so its npm prefixes are `frontend`, not `../frontend`.
- Frontend API base defaults to `http://127.0.0.1:5000`; override with `VITE_API_BASE_URL`. Backend secrets (e.g. `GOOGLE_OAUTH_CLIENT_ID/SECRET`, `GOOGLE_CLOUD_PROJECT`) must never go in `VITE_*` vars.
- DB path defaults to `<repo>/instance/database.db`; override with `COWRITER_DATABASE_URI`. Extra CORS origins via `COWRITER_ALLOWED_ORIGINS`.
- All backend imports use the `backend.` package prefix; `app.py` and `mcp_server.py` patch `sys.path` so they also work as scripts. All routes are under `/api`.
- `npm run dev` is long-running; `Running target/debug/cowriter` means launch succeeded.

## Architecture

### Frontend
- `main.tsx` injects a `CowriterApi` instance into `App` (`App.tsx` holds top-level app state). `services/backend/types.ts` defines the interface; `cowriterApi.ts` implements it, validates responses, and maps snake_case wire fields to frontend types; `http.ts` is the only module that calls `fetch` or knows the base URL. Components contain no transport code.
- Local project files (listing, LaTeX source read/write) do **not** go through Flask: `services/projectFilesystem.ts` calls Rust `#[tauri::command]`s in `src-tauri/src/main.rs`, and only works inside the Tauri runtime.
- UI frame is adapted from the MIT-licensed DeepSeek Harness UI (presentation only, no Harness runtime) — see `THIRD_PARTY_NOTICES.md`.
- `docs/frontend-backend-api.md` documents the API contract.

### Backend
- `app.py` wires Flask, SQLAlchemy, Flask-Migrate, Flask-Admin, registers blueprints from `blueprints/`, and builds a single `ChatService` stored in `app.extensions["chat_service"]` with injected lookups (connection, project, conversation resolver, tool-call service). Route tests swap in fakes via that extension key rather than using the real DB.
- Layers: `blueprints/` (HTTP parsing/validation, persistence ownership) → `services/` (chat, conversation, project, tool-call logic) → `database/models.py`. `database/catalog.py` seeds the provider catalog on startup.
- `llm/contracts.py` defines the provider-agnostic `ChatRequest`, `LLMProvider` protocol (`chat`, `stream_chat`, `complete_chat` with tools, `list_models`), `ToolDefinition`, `ModelTurn`, and `LLMError` (carries an HTTP status).
- Providers live in `auth/providers/` (`Openai.py`, `Ollama.py`, `Gemini.py`); each file has an `*Provider` (LLM calls) and an `*Connector` (connection/auth validation). Credentials are stored in the OS keyring via `auth/credentials.CredentialStore`; Google OAuth flow is in `auth/oauth.py`.
- **Chat flow** (`POST /api/chat` → `ChatService.stream_chat`): resolves provider + connection + keyring credentials. If the request's project has a filesystem `path`, it spawns `backend/mcp_server.py` over stdio (`MCPClient`, `COWRITER_PROJECT_PATH` env) and runs a non-streamed tool loop (`complete_chat`, max `MAX_TOOL_ROUNDS = 5`), persisting each call as a `ToolCall` row (pending → running → completed/failed) on the project's conversation. Otherwise it streams directly from the provider. Async MCP work is bridged to Flask's sync generator via a private event loop.
- Response is NDJSON (`application/x-ndjson`): `assistant_start` / `assistant_delta` / `assistant_end`, `tool_call` (serialized record), then `done` or `error`.
- MCP tools (`tools/files.py`: read-only `read_file`, `list_files`) are sandboxed to the project root — reject absolute paths and anything resolving outside it.

## Provider integration boundary

- Provider objects under `backend/auth/providers/` only talk to and validate external provider APIs. They must not import DB models, query/mutate the DB, use sessions, or persist credentials.
- Flask API routes own all provider-connection persistence (DB records and keyring storage). Providers return normalized connection info for the route to persist.

## Scope limits

Keep AI/provider calls behind the Flask boundary, never from React. Don't add Anthropic, LangChain, LangGraph, RAG, or embeddings integrations unless explicitly requested.
