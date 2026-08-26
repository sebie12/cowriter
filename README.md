# Cowriter

Cowriter is a desktop application for AI-assisted research and writing. It has a React interface, a Tauri desktop shell, and a Flask backend with provider connections and streamed chat.

## Architecture

The app is split into three clear areas:

- `frontend/`: React, TypeScript, and Vite user interface.
- `src-tauri/`: Tauri desktop shell and window configuration.
- `backend/`: Minimal Flask API that represents the future Python AI/backend layer.

The frontend communicates with Flask through the injected `CowriterApi` interface in `frontend/src/services/backend/types.ts`. HTTP paths, wire validation, and NDJSON stream parsing are isolated in `frontend/src/services/backend/`; React components contain no transport code. The complete frontend API contract and the removed Harness capabilities are documented in [`docs/frontend-backend-api.md`](docs/frontend-backend-api.md).

The application frame and conversation presentation are adapted from the MIT-licensed DeepSeek Harness UI packages without importing the Harness runtime. Cowriter retains its own branding and typography. See [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md) for attribution.

## Requirements

- Node.js 20+
- npm
- Python 3.10+
- Rust and Cargo
- Tauri system dependencies for your operating system

On Linux, install the packages listed in the Tauri prerequisites for your distribution: https://tauri.app/start/prerequisites/

## Install Frontend Dependencies

```bash
npm install
npm install --prefix frontend
```

## Install Python Dependencies

```bash
python -m venv backend/.venv
backend/.venv/bin/pip install -r backend/requirements.txt
```

If you prefer to use an already-active virtual environment:

```bash
pip install -r backend/requirements.txt
```

## Initialize The Database

Apply pending database migrations before starting Flask:

```bash
backend/.venv/bin/flask --app backend.app db upgrade
```

After changing a database model, generate and review a new migration, then apply it:

```bash
backend/.venv/bin/flask --app backend.app db migrate -m "describe the change"
backend/.venv/bin/flask --app backend.app db upgrade
```

The SQLite database is stored at `instance/database.db`. Override it with `COWRITER_DATABASE_URI` when needed.

## Run Flask During Development

Start the backend in one terminal:

```bash
backend/.venv/bin/python backend/app.py
```

The Flask API runs at `http://127.0.0.1:5000`.

To start Flask and the Vite frontend together, run this from the repository root:

```bash
python run.py
```

The launcher prefers `backend/.venv` when it exists, otherwise it uses the active Python interpreter. Press Ctrl+C to stop both services.

For Google OAuth connections, configure a Google OAuth web client with this redirect URI:

```text
http://127.0.0.1:5000/api/providers/google_gemini/oauth/callback
```

Then set these backend-only environment variables before starting Flask:

```bash
export GOOGLE_OAUTH_CLIENT_ID="your-client-id"
export GOOGLE_OAUTH_CLIENT_SECRET="your-client-secret"
export GOOGLE_CLOUD_PROJECT="your-google-cloud-project"
export GOOGLE_CLOUD_LOCATION="us-central1"
```

`GOOGLE_CLOUD_LOCATION` defaults to `us-central1`. If the provider ID or backend address differs, set `GOOGLE_OAUTH_REDIRECT_URI` to the registered callback URI. Never expose these values through `VITE_*` frontend variables.

Available endpoints:

- `GET /api/health`
- `POST /api/chat` with `{ "connection_id": 1, "provider": "ollama", "model": "qwen3:8b", "message": "Hello", "system_prompt": "Optional instructions", "history": [] }`

Provider and model endpoints used by the frontend are listed in [`docs/frontend-backend-api.md`](docs/frontend-backend-api.md).

## Run The Tauri App

With Flask running, start the desktop app in another terminal:

```bash
npm run dev
```

Tauri starts the Vite frontend automatically and opens the desktop window.

## Frontend Structure

```text
frontend/src/
├── components/
│   ├── Conversation.tsx
│   ├── conversation/
│   │   └── MessageItem.tsx
│   ├── MarkdownContent.tsx
│   ├── Sidebar.tsx
│   ├── Workspace.tsx
│   └── composer/
│       ├── Composer.tsx
│       └── ModelSelector.tsx
├── data/
│   └── mockProjects.ts
├── services/
│   ├── backend/
│   │   ├── cowriterApi.ts
│   │   ├── http.ts
│   │   └── types.ts
│   └── externalLinks.ts
├── types/
│   └── index.ts
├── utils/
│   └── ids.ts
├── App.tsx
├── main.tsx
└── styles.css
```

## Currently Mocked

- Project data is stored only in React state for the current session.
- New projects are local-only and are not persisted.
- Chat responses come from the configured OpenAI or local Ollama model through `POST /api/chat`.
- The current chat transport supports text messages only; attachment controls are omitted until the backend supports them.
- No Anthropic, LangChain, LangGraph, MCP, embeddings, or RAG integration is included.

## Future Direction

The structure is intended to evolve toward projects with documents, sources, citations, conversations, and writing sessions. The Flask layer is reserved for future LLM orchestration, RAG, MCP servers/tools, document processing, embeddings, agent workflows, and evaluation/observability.
