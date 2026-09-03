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

These are the only backend routes called by the retained frontend. Paths reflect the existing Flask backend, including the current lack of an `/api` prefix on provider-connection routes.

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

Response: `application/x-ndjson`. Each event is one JSON object followed by a newline.

```json
{"type":"delta","content":"First text chunk"}
{"type":"delta","content":" and another chunk"}
{"type":"done"}
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

When the selected project has a filesystem path, the backend starts the bundled MCP server for that project, sends its `read_file` and `list_files` definitions to the model, executes requested tools, and returns only the model's final text through the existing NDJSON events. Tool-enabled turns are buffered until tool execution finishes. Paths accepted by the MCP tools are relative to the selected project root and cannot escape it.

Required: yes.

Cancellation: the frontend aborts the HTTP request. A separate cancel endpoint is not required. Prompt provider work should stop when the backend detects client disconnect if the provider supports cancellation.

Replaces:

- Harness `session.prompt`.
- The text-output subset of Harness `session/event` streaming.
- The text-output subset of the Harness agent/session prompt pipeline.
- Harness `session.cancel` is replaced on the client by aborting this request.

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
GET /provider-connections/
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
GET /provider-connections/:connectionId/models
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

- Sidebar project creation and selection use React session state seeded by `frontend/src/data/mockProjects.ts`.
- Active provider connection and per-connection model preference use `localStorage` key `cowriter.chat-preferences.v1`.
- Message copy uses the browser clipboard API.
- Stop response uses `AbortController` on the active `/api/chat` request.
- Conversation zoom, bottom-follow, jump-to-latest, streaming status, and error/stopped presentation are client behavior.

Project messages are not durable across an application reload. The existing `GET /api/projects` and `POST /api/projects` routes are intentionally not called because they do not provide the append/update operations required for a complete conversation persistence flow. No speculative conversation endpoints were added to the frontend contract.

## Harness API Replacement Inventory

### Replaced by the Cowriter API

| Harness frontend dependency | Cowriter replacement |
| --- | --- |
| `session.prompt` | `POST /api/chat` |
| `session.cancel` | Abort the active `/api/chat` request |
| `session/event` assistant text frames | NDJSON `delta`, `done`, and `error` events |
| `session.models`, `llm.models` | `GET /provider-connections/:connectionId/models` |
| `llm.providers` and LLM adapter registry | `GET /api/providers/` |
| Provider route/configuration state | `GET /provider-connections/` |
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

Original APIs removed: `host.pickDirectory`, `host.listDirectory`, `host.createDirectory`, `host.openPath`, `fileReferences.list`, `sessionReferenceResolver.candidates`, `skill.list`, and all tool-call/event rendering contracts.

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

- Durable project and conversation history, including message append/update.
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
