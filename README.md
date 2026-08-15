# Cowriter

Cowriter is an early desktop foundation for AI-assisted research and writing. This version establishes the application shell, frontend architecture, and Python backend boundary without integrating any real AI providers or document-processing systems yet.

## Architecture

The app is split into three clear areas:

- `frontend/`: React, TypeScript, and Vite user interface.
- `src-tauri/`: Tauri desktop shell and window configuration.
- `backend/`: Minimal Flask API that represents the future Python AI/backend layer.

The frontend communicates with Flask over HTTP through a small API client in `frontend/src/services/api.ts`. Current responses are mocked so future LLM, RAG, MCP, embeddings, and document workflows can be added behind the backend API without rewriting the UI.

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

## Run Flask During Development

Start the backend in one terminal:

```bash
backend/.venv/bin/python backend/app.py
```

The Flask API runs at `http://127.0.0.1:5000`.

Available endpoints:

- `GET /api/health`
- `POST /api/chat` with `{ "message": "Hello" }`

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
│   ├── MarkdownContent.tsx
│   ├── Sidebar.tsx
│   ├── Workspace.tsx
│   └── composer/
│       └── Composer.tsx
├── data/
│   └── mockProjects.ts
├── services/
│   └── api.ts
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
- Chat responses come from `POST /api/chat` and return a deterministic placeholder message.
- Attachment, model/tool controls, settings, and account/profile controls are visual placeholders only.
- No OpenAI, Anthropic, LangChain, LangGraph, MCP, local model, database, embeddings, or RAG integration is included.

## Future Direction

The structure is intended to evolve toward projects with documents, sources, citations, conversations, and writing sessions. The Flask layer is reserved for future LLM orchestration, RAG, MCP servers/tools, document processing, embeddings, agent workflows, and evaluation/observability.
