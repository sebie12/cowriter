# Cowriter frontend backend API

## Scope

The active Cowriter frontend is a standalone React/Vite application. It does not boot the DeepSeek Harness client module system and does not import Cordis, generated RPC clients, Harness session objects, or Harness runtime packages.

The runtime path is:

```text
React components
  -> CowriterApi interface
  -> HTTP Cowriter API adapter
  -> existing Flask backend
```

`frontend/src/services/backend/types.ts` is the UI-facing interface. `frontend/src/services/backend/cowriterApi.ts` implements it, validates backend responses, and translates snake_case wire fields into frontend types. `frontend/src/services/backend/http.ts` is the only module that knows the API base URL or calls `fetch`.

The visible application frame is a standalone Cowriter adaptation of the MIT-licensed DeepSeek Harness presentation layer. It ports the frame/sidebar geometry, workspace session rows, conversation skeleton and message layout, empty-session hero, composer, hierarchical model selector, settings shell, icons, and theme tokens from the Harness `ui-layout`, `ui-sidebar`, `ui-workspace`, `ui-conversation`, `ui-model-selection`, `ui-settings-general`, `ui-primitives`, and `ui-theme` packages. The port retains Cowriter's logo, SN Pro interface font, and Atkinson Hyperlegible conversation font. Harness Cordis services, slots, stores, RPC types, sessions, tools, and coding-agent controls are not part of the port.

The default base URL is `http://127.0.0.1:5000`. `VITE_API_BASE_URL` overrides it.

## Required API

These are the backend routes called by the retained frontend. All application routes use the `/api` prefix.

Project selection records its last-opened time with `POST /api/projects/:projectId/open` (no request body). Tool-call history is available at `GET /api/conversations/:conversationId/tool-calls`. Provider connections are created or reconnected only through `POST /api/providers/:providerId/connect`; direct `POST /api/provider-connections/` is not supported.

### Stream a chat response

```text
POST /api/chat
```

Purpose: submit the latest writing prompt and stream the assistant message into the conversation.

Used by: composer, conversation stream state, Stop response action, error state.

Request:

```json
{
  "project_id": 12,
  "connection_id": 4,
  "provider": "openai",
  "model": "gpt-4.1",
  "message": "Help me tighten this introduction.",
  "system_prompt": null,
  "history": [
    { "role": "user", "content": "Earlier prompt" },
    { "role": "assistant", "content": "Earlier response" }
  ]
}
```

`project_id`, `title`, and `description` are optional. When `project_id` is set, the backend saves the chat to the project's conversation: the user message once the response starts, and each assistant segment when it ends (or, if the response errors or is stopped, whatever text it had so far). Requests rejected before streaming save nothing. In the tool loop (every request with a `project_id`), the backend ignores the client's `history` and rebuilds earlier turns from the saved conversation instead, including earlier tool calls with their results shortened to 1,200 characters; the oldest turns are dropped once the history passes half of the model's context window. When `system_prompt` is omitted, the backend builds a default chat prompt from `title` and `description`.

Response: `application/x-ndjson`. Each event is one JSON object followed by a newline. Assistant text arrives as keyed message segments; one response may contain several segments when tools are used.

```json
{"type":"assistant_start","id":"assistant-3f1c...","created_at":"2026-09-19T10:00:00Z"}
{"type":"assistant_delta","id":"assistant-3f1c...","content":"First text chunk"}
{"type":"assistant_delta","id":"assistant-3f1c...","content":" and another chunk"}
{"type":"assistant_end","id":"assistant-3f1c...","finished_at":"2026-09-19T10:00:01Z"}
{"type":"done"}
```

During tool-enabled turns, each state change of a tool call is emitted as a `tool_call` event carrying the persisted record. Status moves `pending` → `running` → `completed` or `failed`, and the frontend replaces the previous state by `id`.

```json
{"type":"tool_call","tool_call":{"id":7,"conversation_id":3,"provider_call_id":"call_abc","tool_name":"read_file","input_data":{"path":"main.tex"},"output_data":null,"status":"running","error":null,"created_at":"2026-09-19T10:00:00Z","completed_at":null}}
```

An error after streaming starts is:

```json
{"type":"error","error":"Provider error message"}
```

An error before streaming starts is a non-2xx JSON response:

```json
{"error":"Validation or provider error"}
```

Streaming: required, using NDJSON over the Fetch response body. SSE and WebSocket support are not required.

When the selected project has a filesystem path, the backend starts the bundled MCP server for that project, sends its `read_file` and `list_files` definitions to the model, and runs up to five tool rounds. Each tool call is persisted to the project's conversation and reported through `tool_call` events. In tool-enabled turns, model text is not streamed token by token: each model turn's text is sent as one complete `assistant_start`/`assistant_delta`/`assistant_end` segment. Paths accepted by the MCP tools are relative to the selected project root and cannot escape it. Every request with a `project_id` also gets the in-process `update_project_settings` tool, which changes the project's title and/or writing settings (only the fields it is given) and returns `{ "name", "description", "settings" }`; rejected values come back to the model as a tool error. Because of it, project chats always use the non-streamed tool loop, even without a filesystem path. When this tool call completes, the frontend applies the returned title and description to the open project. `read_file` returns `.tex` and `.docx` files as plain text (converted with pandoc) and returns long files in pages (`content`, `offset`, `next_offset`, `total_chars`, `truncated`). The backend limits each page to the context the selected model has left, and if no context is left the call is recorded as `failed` without reading the file.

Required: yes.

Cancellation: the frontend aborts the HTTP request. A separate cancel endpoint is not required. Prompt provider work should stop when the backend detects client disconnect if the provider supports cancellation.

Replaces:

- Harness `session.prompt`.
- The text-output subset of Harness `session/event` streaming.
- The text-output subset of the Harness agent/session prompt pipeline.
- Harness `session.cancel` is replaced on the client by aborting this request.

### List projects

```text
GET /api/projects
```

Purpose: load the sidebar project list on startup.

Response: an array of project objects.

```json
[
  {
    "id": 12,
    "name": "Thesis",
    "description": "Use an academic tone.\nUse a formal writing style.\n...",
    "settings": {
      "tone": "Academic",
      "writing_style": "Formal",
      "academic_level": "Graduate",
      "language": "English",
      "essay_type": "Argumentative",
      "additional_instructions": null
    },
    "path": "/home/user/thesis",
    "conversations": [
      { "id": 3, "project_id": 12, "messages": [], "tool_calls": [], "created_at": "...", "updated_at": "..." }
    ],
    "created_at": "...",
    "updated_at": "...",
    "opened_at": "..."
  }
]
```

`settings` holds the structured writing settings and `description` is the prose prompt rendered from them; both, and `path`, may be `null`. The frontend merges each conversation's `messages` and `tool_calls` into its chat view, ordered by `created_at`.

### Delete a project's chat

```text
DELETE /api/projects/:id/conversation
```

Deletes the project's chat: its conversations, messages, and tool calls. The next chat message starts a new conversation. Response: `204`, or `404` for an unknown project.

### Create a project

```text
POST /api/projects
```

Request: `{ "name": "Thesis", "description": { ... } | null, "path": "/abs/path" | null }`. `description` fields must use the allowed values in `SETTING_OPTIONS` (`backend/services/project_settings.py`); they are stored as `settings` and rendered into `description`.

Response: `201` with the created project object. `400` on validation errors, `409` if the name or path already exists.

### Mark a project opened

```text
POST /api/projects/:projectId/open
```

No request body. Updates `opened_at` and returns the project, or `404`.

### Save a project draft

```text
PUT /api/projects/:projectId/draft
```

Request: `{ "draft": { "type": "doc", ... } | null }`, the TipTap/ProseMirror JSON of the Work tab draft. The frontend debounces saves (800 ms) and flushes them when the user switches projects. Project objects include the saved `draft` (or `null`).

Response: `200` with `{ "draft", "updated_at" }`. `400` if `draft` is missing or not a `doc` node, `413` if the body is larger than 2 MB, `404` for an unknown project.

### Search papers

```text
GET /api/research/search?q=<query>&offset=<n>
```

Proxies the OpenAlex works search (`https://api.openalex.org/works?search=…`, 20 results per page). `offset` is rounded down to a page boundary, and OpenAlex only pages through the first 10,000 results. The backend sends `OPENALEX_API_KEY` as `api_key` when that variable is set. Without a key, requests share a small free daily budget per IP address. OpenAlex returns abstracts as an inverted index, which the backend turns back into text. OpenAlex has no TLDRs, so `tldr` is always `null`.

Response:

```json
{
  "total": 1234,
  "offset": 0,
  "next": 20,
  "papers": [
    {
      "paper_id": "W2741809807",
      "title": "Attention Is All You Need",
      "year": 2017,
      "authors": ["Ashish Vaswani", "Noam Shazeer"],
      "venue": "Neural Information Processing Systems",
      "abstract": "...",
      "tldr": null,
      "citation_count": 100000,
      "doi": "10.48550/arXiv.1706.03762",
      "url": "https://openalex.org/W2741809807",
      "pdf_url": "https://arxiv.org/pdf/1706.03762"
    }
  ]
}
```

`next` is `null` on the last page. Errors: `400` for an empty or over-300-character query or an invalid offset, `429` when OpenAlex rate-limits, and `502` when it is unreachable.

### Saved references

```text
GET    /api/projects/:projectId/references
POST   /api/projects/:projectId/references
DELETE /api/projects/:projectId/references/:referenceId
```

A reference is a paper (the same fields as a search result) plus `id`, `project_id` and `created_at`. `POST` takes a paper object and returns `201` with the reference. It returns `409` with `{ "error", "reference" }` if that `paper_id` is already saved for the project. `DELETE` returns `204`, or `404` if the reference belongs to another project. References are deleted along with their project.

### Proofread a draft

```text
POST /api/projects/:projectId/proofread
```

Request: `{ "connection_id": 1, "provider": "ollama", "model": "qwen3:8b", "text": "<plain text of the draft>" }`.

The selected model reviews `text` using:
- the project's writing instructions
- its saved references (title, authors, year, and TLDR or abstract excerpt)
- the project's files, via the read-only MCP tools, when the project has a folder. These tool calls are not recorded in the chat history.
- the project's essay, when the project has a folder. The backend picks the `.tex` file that contains `\begin{document}` (or the largest `.tex` file), inlines its `\input`/`\include` chapters (skipping preambles and anything outside the folder), converts it to plain text with pandoc, and caps it at 24,000 characters. The essay is placed in the user message, followed by an instruction to check the draft sentence by sentence and report contradictions as `claim` issues.

The model's reply is constrained to JSON matching a schema (Ollama `format`, OpenAI JSON mode). Constraints can't be combined with tool calls, so when the project has a folder the tool rounds run unconstrained. If the last answer isn't valid JSON, one more turn without tools asks for it again under the constraint. Replies that still can't be parsed are logged as a warning on the server. The backend finds each quoted passage in `text` and computes the character offsets itself. Issues whose quote can't be found are dropped.

Response:

```json
{
  "essay_file": "main.tex",
  "essay_truncated": false,
  "topic": { "on_topic": false, "explanation": "The essay is about carbon taxes; the draft is a recipe." },
  "issues": [
    {
      "id": "issue-…",
      "type": "spelling | grammar | claim | style",
      "start": 0,
      "end": 3,
      "quote": "teh",
      "explanation": "Misspelling of “the”.",
      "suggestion": "the",
      "reference_ids": []
    }
  ]
}
```

`essay_file` is the project-relative essay the draft was compared with (`null` when there is no folder or no `.tex` file), and `essay_truncated` says whether it was cut. With an essay, the model also judges whether the draft is about the essay's topic at all: `topic.on_topic` is `false` only when the draft has nothing to do with it (a new angle or section of the same subject counts as on topic). The schema then asks for `topic` before `issues`. `topic` is `null` without an essay, or when the model gives no readable verdict (the review doesn't fail over it); the Feedback panel shows an "Off topic" note when it is `false`. For Ollama, the request sets `num_ctx` to fit the prompt (about 3 characters per token plus 2,048 tokens for the answer, between 4,096 and 32,768). `suggestion` is replacement text for `quote`, or `null`. `reference_ids` only contains ids of the project's saved references. Errors: `400` for validation, `413` for drafts over 60,000 characters, provider errors with their own status, and `502` when the model's reply is not valid JSON.

The frontend builds `text` by joining text blocks with a blank line (`"\n\n"`), the same way as ProseMirror `textBetween`, and maps the offsets back to editor positions. The editor is read-only while a review runs.

### List supported providers

```text
GET /api/providers/
```

Purpose: populate provider settings and determine which providers support chat.

Used by: Settings > Model Providers, active connection filtering.

Request: no payload.

Response:

```json
[
  {
    "id": "openai",
    "name": "OpenAI",
    "description": "Connect to OpenAI using an API key.",
    "chat_supported": true,
    "auth_methods": ["api_key"]
  },
  {
    "id": "ollama",
    "name": "Ollama",
    "description": "Connect to an Ollama server running on this computer.",
    "chat_supported": true,
    "auth_methods": ["local"]
  }
]
```

Streaming: no.

Required: yes.

Replaces:

- Harness `llm.providers`.
- The provider-list portion of the Harness LLM adapter registry.
- The provider schema portion of Harness model settings.

### List provider connections

```text
GET /api/provider-connections/
```

Purpose: populate configured accounts/endpoints and select the connection used for chat.

Used by: provider settings, active provider selection, initial chat configuration.

Request: no payload.

Response:

```json
[
  {
    "id": 4,
    "provider": "openai",
    "auth_method": "api_key",
    "auth_method_id": 2,
    "account_id": "openai-api-key-fingerprint",
    "account_label": "OpenAI API key",
    "endpoint_url": null,
    "status": "connected",
    "expires_at": null,
    "created_at": "2026-08-26T12:00:00Z",
    "updated_at": "2026-08-26T12:00:00Z"
  }
]
```

The frontend consumes `id`, `provider`, `auth_method`, `account_label`, `endpoint_url`, `status`, `created_at`, and `updated_at`. Extra fields may be present.

Streaming: no.

Required: yes.

Replaces:

- Harness `credentials.describe` for provider connection status.
- Harness settings-backed provider configuration reads.
- The configured-route portion of Harness model selection.

### List models for a connection

```text
GET /api/provider-connections/:connectionId/models
```

Purpose: populate the model selector for the active provider connection.

Used by: workspace model selector and persisted per-connection model preference.

Request: path parameter only. `connectionId` is a positive integer returned by the connection list.

Response:

```json
{
  "connection_id": 4,
  "provider": "openai",
  "models": [
    { "id": "gpt-4.1", "name": "gpt-4.1" }
  ]
}
```

The frontend requires each model to have a non-empty string `id`. `name` is optional.

Streaming: no.

Required: yes for chat. A connected provider with no returned models cannot send a message.

Replaces:

- Harness `llm.models`.
- Harness `session.models`.
- The model-list portion of the Harness model-selection service.

### Connect a provider

```text
POST /api/providers/:providerId/connect
```

Purpose: configure and validate a provider connection from settings.

Used by: API-key, local-server, and OAuth connection flows.

Request:

```json
{
  "auth_method": "api_key",
  "api_key": "secret when required",
  "account_label": "Optional display label",
  "server_url": "Optional local provider URL"
}
```

Immediate success response:

```json
{
  "id": 4,
  "provider": "openai",
  "auth_method": "api_key",
  "account_label": "OpenAI API key",
  "endpoint_url": null,
  "status": "connected",
  "created_at": "2026-08-26T12:00:00Z",
  "updated_at": "2026-08-26T12:00:00Z"
}
```

OAuth-start response:

```json
{
  "provider": "gemini",
  "status": "connecting",
  "attempt_id": "opaque-attempt-id",
  "authorization_url": "https://provider.example/authorize"
}
```

Streaming: no.

Required: yes for the retained provider-configuration UI. It can be omitted only in a deployment that removes that UI and provisions all connections externally.

Replaces:

- Harness `credentials.set` for provider secrets.
- Harness settings update/mutate operations used by model-provider settings.
- Harness provider-specific onboarding writes and model discovery validation.

Security capability: secret persistence and provider API validation belong to the Flask route and provider layer. The frontend does not persist API keys.

### Poll OAuth connection status

```text
GET /api/providers/:providerId/oauth/status/:attemptId
```

Purpose: finish an OAuth provider connection after the authorization page opens.

Used by: OAuth connection panel. The frontend polls every two seconds for up to five minutes.

Request: path parameters only.

Response while pending:

```json
{
  "provider": "gemini",
  "status": "connecting"
}
```

Response after success:

```json
{
  "provider": "gemini",
  "status": "connected"
}
```

Response after failure:

```json
{
  "provider": "gemini",
  "status": "error",
  "error": "Authorization failed"
}
```

Streaming: no.

Required: optional. It is required only when a provider from `GET /api/providers/` advertises `oauth` in `auth_methods`.

Replaces:

- Harness credential-reference update events for an interactive provider authorization flow.
- Harness credential status refresh after provider onboarding.

### OAuth callback capability

```text
GET /api/providers/:providerId/oauth/callback
```

Purpose: receive the external provider redirect, exchange the authorization code, and update the attempt read by the status endpoint.

Used by: the external browser, not directly by React. Its URL is normally embedded in the authorization request initiated by the connect endpoint.

Request: provider-defined query fields, including the opaque OAuth `state` and authorization `code`.

Response: an HTML success/failure page suitable for the external browser. The connection result must also become visible through the OAuth status and provider-connection endpoints.

Streaming: no.

Required: optional. It is part of the OAuth capability only.

Replaces: the callback/credential completion portion of Harness provider onboarding.

## Client-Local Features

The following retained features do not require backend endpoints:

- Listing files inside a project directory uses Tauri commands (`frontend/src/services/projectFilesystem.ts` → `src-tauri/src/main.rs`), not Flask, and is only available in the desktop app.
- Active provider connection and per-connection model preference use `localStorage` key `cowriter.chat-preferences.v1`. The Work tab's review uses the same selection.
- Proofreading highlights, filters, Apply and Dismiss are client state. Applying a suggestion edits the draft, and any edit to a highlighted passage removes its issue.
- Message copy uses the browser clipboard API.
- Stop response uses `AbortController` on the active `/api/chat` request.
- Conversation zoom, bottom-follow, jump-to-latest, streaming status, and error/stopped presentation are client behavior.

Projects and tool calls are persisted by the backend, but chat messages are not: `/api/chat` does not append user or assistant messages to the conversation, so messages exchanged after a project is created are lost on reload. No speculative message-append endpoints were added to the frontend contract.

## Harness API Replacement Inventory

### Replaced by the Cowriter API

| Harness frontend dependency | Cowriter replacement |
| --- | --- |
| `session.prompt` | `POST /api/chat` |
| `session.cancel` | Abort the active `/api/chat` request |
| `session/event` assistant text frames | NDJSON `assistant_start`, `assistant_delta`, `assistant_end`, `tool_call`, `done`, and `error` events |
| `session.models`, `llm.models` | `GET /api/provider-connections/:connectionId/models` |
| `llm.providers` and LLM adapter registry | `GET /api/providers/` |
| Provider route/configuration state | `GET /api/provider-connections/` |
| Provider credential/settings writes | `POST /api/providers/:providerId/connect` |
| Credential refresh during OAuth | OAuth status and callback capability |

### Replaced by ordinary React composition

| Harness mechanism | Cowriter replacement |
| --- | --- |
| `window.__DSH_BOOT__` | Static Vite entrypoint in `frontend/src/main.tsx` |
| `ClientModuleSystem` and dynamic client bundles | Normal ESM imports |
| Cordis Loader and browser plugin activation | React component tree |
| `ctx.slots.register` and slot renderer | Explicit typed component props |
| `ctx.sessions` observable object layer | React project/message state |
| Harness stream folding/session projection | One keyed assistant message updated from typed stream events |
| `ctx.connection`, API proxy, gateway, and generated RPC carrier | Injected `CowriterApi` interface |
| Harness reconnecting WebSocket streams | One Fetch request per chat response and ordinary HTTP provider reads |

## Intentionally Removed Harness Capabilities

These coding-agent or runtime-management features are not used by the Cowriter frontend and need no replacement endpoint.

### Coding execution and repository context

- Shell, bash, PowerShell, persistent terminal, subprocess, and process-tree execution.
- Filesystem write/edit, grep/glob, diff, repository file references, and native open-path behavior. The backend does provide project-scoped read-only MCP tools for reading and listing files.
- Workspace directory picking, directory listing/creation, and coding workspace roots.
- Repository instructions, skills, coding deliverables, produced files, and session file mentions.
- Sandbox, E2B, Landlock, local execution policy, and permission presets for tool execution.
- LSP and coding-specific syntax/tool result surfaces.

Original APIs removed: `host.pickDirectory`, `host.listDirectory`, `host.createDirectory`, `host.openPath`, `fileReferences.list`, `sessionReferenceResolver.candidates`, `skill.list`, and the Harness tool-call/event rendering contracts (Cowriter renders its own `tool_call` stream events).

### Agent orchestration

- Agent loop, system-prompt pipeline, plan mode, goal execution, retries, compaction internals, and max-token turn nodes.
- Subagents, addressed subagent transcripts, parent/child lineage, delegation, and interruption.
- Background jobs, workflows, workflow workers, and durable workflow-run nodes.
- User approvals, agent questions, plan review, and RPC response correlation.
- Dynamic Cordis package definition/execution and runtime self-modification.
- Agent presets and per-session agent composition.

Original APIs removed: all `subagent.*`, `goal.*`, `agentPreset.*`, `respond`, `commands.*`, and `dynamicCordisRunner.*` operations, plus approval/question/job/projection stream frames.

### Harness session and workspace management

- Host-backed session listing, searching, creation, history paging, rename, fork, queueing, steering, and archive.
- Host-backed workspace listing, creation, rename, deletion, ordering, and session ordering.
- Host session status, reconnect projections, archived-session changes, and workspace events.

Original APIs removed: `session.list`, `session.search`, `session.create`, `session.history`, `session.rename`, `session.fork`, `session.attachment`, `session.updateQueue`, all `workspace.*` operations, and all host/session WebSocket streams.

The Cowriter project sidebar remains client-local. Durable project/conversation history is therefore a known unsupported feature, not an implied backend endpoint.

### Harness settings and plugin management

- Plugin inventory and plugin-specific settings cards.
- Opening or replacing local Harness settings documents.
- Bash, Web search, agent-loop, and agent-preset settings.
- Dynamic model-provider schema editing and arbitrary model discovery drafts.
- Harness theme/locale settings synchronization events.

Original APIs removed: `settings.describe`, `settings.openDocument`, `settings.update`, `settings.replace`, `settings.mutate`, `credentials.describe`, `credentials.unset`, `llm.discoverModels`, and `pluginInventory.list`.

Cowriter retains its existing provider settings and visual branding. Provider secrets are configured only through the Cowriter provider connect route.

### Feedback and telemetry

- Per-message like/dislike records and versioned notes.
- Harness session telemetry, OpenTelemetry projection, token meter, and session statistics.
- Host description and Harness build/plugin metadata.

Original APIs removed: all `messageFeedback.*` operations and `host.describe`.

## Frontend Features Requiring Future Backend Support

The following Harness experiences were not preserved because the existing Cowriter backend does not expose the corresponding writing-oriented data:

- Durable conversation history, including message append/update (projects themselves are persisted).
- Conversation search, rename, delete, fork, and archive.
- History pagination for long conversations.
- Image or document attachments.
- Server-provided citations, structured writing artifacts, reasoning sections, token usage, or finish reasons.
- Message feedback persistence.
- Server-side cancellation confirmation. Client cancellation is available now through request abort.

Endpoints for these features are deliberately omitted until the frontend retains a feature that calls them and the backend has a concrete data contract.

## Removed Runtime Modules

The active frontend no longer requires these Harness layers:

- `packages/client/web` boot and seed code.
- `packages/client/modules` dynamic module system.
- `packages/client/connection` and its reconnecting RPC/WebSocket carriers.
- `packages/api/gateway` and `packages/api/remotes` generated RPC services.
- `packages/client/runtime` sessions, workspaces, projections, stream folding, and stores.
- `packages/client/ui-slots` and `packages/client/ui-renderer`.
- Cordis and Cordis Loader.
- Coding feature UI packages for tools, workspace directories, commands, references, skills, subagents, jobs, goals, permissions, plans, workflows, trajectories, deliverables, and agent presets.
- Host API proxy, Web runtime glue, worker runtime, session projection cache, plugin inventory, and agent-preset registry.

`deepseek-harness/` remains source/reference material in the repository, but no file under `frontend/src` imports it. The retained frontend therefore has no runtime coupling to Harness. The upstream license notice is preserved in `THIRD_PARTY_NOTICES.md`.
