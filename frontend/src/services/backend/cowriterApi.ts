import type {
  ConnectProviderInput,
  OAuthConnectionStatus,
  ProviderAuthorization,
  ProviderConnection,
  ProviderConnectionStatus,
  ProviderModel,
  SupportedProvider,
} from "../../types/providers";
import type { Message, Project } from "../../types";
import { request, requestJson } from "./http";
import type { ChatStreamEvent, CowriterApi } from "./types";

interface ProviderConnectionResponse {
  id?: unknown;
  provider?: unknown;
  auth_method?: unknown;
  account_label?: unknown;
  endpoint_url?: unknown;
  status?: unknown;
  created_at?: unknown;
  updated_at?: unknown;
}

interface ProjectResponse {
  id?: unknown;
  name?: unknown;
  description?: unknown;
  path?: unknown;
  conversations?: unknown;
  created_at?: unknown;
  updated_at?: unknown;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function normalizeProviderId(value: string): string {
  return value.trim().toLowerCase().replace(/[\s-]+/g, "_");
}

function normalizeAuthMethod(value: string): string {
  const normalized = value.trim().toLowerCase().replace(/[\s.-]+/g, "_");
  if (["oauth", "oauth2", "oauth_2", "oauth_2_0"].includes(normalized)) {
    return "oauth";
  }
  if (["api_key", "apikey"].includes(normalized)) {
    return "api_key";
  }
  return normalized;
}

function normalizeStatus(value: unknown): ProviderConnectionStatus {
  return value === "disconnected" || value === "connecting" || value === "connected" || value === "error"
    ? value
    : "disconnected";
}

function normalizeStringList(value: unknown): string[] {
  return Array.isArray(value)
    ? value.filter((item): item is string => typeof item === "string" && item.trim().length > 0)
    : [];
}

function normalizeProviderConnection(value: unknown): ProviderConnection {
  if (!isRecord(value)) {
    throw new Error("Backend returned an invalid provider connection.");
  }
  const connection = value as ProviderConnectionResponse;
  if (
    typeof connection.id !== "number"
    || typeof connection.provider !== "string"
    || typeof connection.auth_method !== "string"
    || typeof connection.account_label !== "string"
  ) {
    throw new Error("Backend returned an invalid provider connection.");
  }
  return {
    id: connection.id,
    providerId: normalizeProviderId(connection.provider),
    authType: normalizeAuthMethod(connection.auth_method),
    accountLabel: connection.account_label,
    endpointUrl: typeof connection.endpoint_url === "string" ? connection.endpoint_url : undefined,
    createdAt: typeof connection.created_at === "string" ? connection.created_at : undefined,
    updatedAt: typeof connection.updated_at === "string" ? connection.updated_at : undefined,
    status: normalizeStatus(connection.status),
  };
}

function normalizeProjectMessage(value: unknown): Message | null {
  if (
    !isRecord(value)
    || typeof value.id !== "number"
    || (value.role !== "user" && value.role !== "assistant")
    || typeof value.content !== "string"
    || typeof value.created_at !== "string"
  ) {
    return null;
  }
  return {
    id: String(value.id),
    role: value.role,
    content: value.content,
    createdAt: value.created_at,
    status: "complete",
  };
}

function normalizeProject(value: unknown): Project {
  if (!isRecord(value)) {
    throw new Error("Backend returned an invalid project.");
  }
  const project = value as ProjectResponse;
  if (
    typeof project.id !== "number"
    || typeof project.name !== "string"
    || (project.description !== null && typeof project.description !== "string")
    || (project.path !== null && typeof project.path !== "string")
    || !Array.isArray(project.conversations)
    || typeof project.created_at !== "string"
    || typeof project.updated_at !== "string"
  ) {
    throw new Error("Backend returned an invalid project.");
  }

  const messages = project.conversations.flatMap((conversation) => {
    if (!isRecord(conversation) || !Array.isArray(conversation.messages)) {
      throw new Error("Backend returned an invalid project conversation.");
    }
    return conversation.messages
      .map(normalizeProjectMessage)
      .filter((message): message is Message => message !== null);
  });

  return {
    id: String(project.id),
    title: project.name,
    path: project.path,
    writingContext: project.description,
    writingContent: "",
    createdAt: project.created_at,
    updatedAt: project.updated_at,
    messages,
  };
}

function normalizeProvider(value: unknown): SupportedProvider {
  if (!isRecord(value) || typeof value.id !== "string" || typeof value.name !== "string") {
    throw new Error("Backend returned an invalid provider.");
  }
  return {
    id: normalizeProviderId(value.id),
    name: value.name,
    description: typeof value.description === "string" ? value.description : undefined,
    authMethods: Array.from(new Set(normalizeStringList(value.auth_methods).map(normalizeAuthMethod))),
    chatSupported: value.chat_supported === true,
  };
}

function processStreamLine(line: string): ChatStreamEvent | { type: "error"; error: string } | null {
  if (!line.trim()) {
    return null;
  }
  let value: unknown;
  try {
    value = JSON.parse(line);
  } catch {
    throw new Error("Backend returned an invalid chat stream.");
  }
  if (!isRecord(value) || typeof value.type !== "string") {
    throw new Error("Backend returned an invalid chat stream.");
  }
  if (value.type === "delta" && typeof value.content === "string") {
    return { type: "delta", content: value.content };
  }
  if (value.type === "done") {
    return { type: "done" };
  }
  if (value.type === "error" && typeof value.error === "string") {
    return { type: "error", error: value.error };
  }
  throw new Error("Backend returned an invalid chat stream.");
}

export const cowriterApi: CowriterApi = {
  async listProjects(signal) {
    const projects = await requestJson<unknown>("/api/projects", { signal });
    if (!Array.isArray(projects)) {
      throw new Error("Backend returned an invalid project list.");
    }
    return projects.map(normalizeProject);
  },

  async createProject(input, signal) {
    const project = await requestJson<unknown>("/api/projects", {
      method: "POST",
      signal,
      body: JSON.stringify({
        name: input.name,
        description: input.writingContext
          ? {
              tone: input.writingContext.tone,
              writing_style: input.writingContext.writingStyle,
              academic_level: input.writingContext.academicLevel,
              language: input.writingContext.language,
              essay_type: input.writingContext.essayType,
              additional_instructions: input.writingContext.additionalInstructions,
            }
          : null,
        path: input.path,
      }),
    });
    return normalizeProject(project);
  },

  async streamChat(input, onEvent, signal) {
    const response = await request("/api/chat", {
      method: "POST",
      signal,
      body: JSON.stringify({
        connection_id: input.connectionId,
        provider: input.provider,
        model: input.model,
        message: input.message,
        title: input.projectTitle,
        description: input.projectDescription,
        system_prompt: input.systemPrompt,
        history: input.history ?? [],
      }),
    });
    if (!response.body) {
      throw new Error("Backend returned an unreadable chat stream.");
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    let finished = false;

    const emitLine = (line: string) => {
      const event = processStreamLine(line);
      if (event === null) {
        return;
      }
      if (event.type === "error") {
        throw new Error(event.error);
      }
      if (event.type === "done") {
        finished = true;
      }
      onEvent(event);
    };

    try {
      while (!finished) {
        const { value, done } = await reader.read();
        buffer += decoder.decode(value, { stream: !done });
        let newlineIndex = buffer.indexOf("\n");
        while (newlineIndex >= 0) {
          emitLine(buffer.slice(0, newlineIndex));
          buffer = buffer.slice(newlineIndex + 1);
          if (finished) {
            break;
          }
          newlineIndex = buffer.indexOf("\n");
        }
        if (done) {
          if (!finished && buffer.trim()) {
            emitLine(buffer);
          }
          break;
        }
      }
    } finally {
      reader.releaseLock();
    }
    if (!finished) {
      throw new Error("Backend chat stream ended unexpectedly.");
    }
  },

  async listProviders(signal) {
    const providers = await requestJson<unknown>("/api/providers/", { signal });
    if (!Array.isArray(providers)) {
      throw new Error("Backend returned an invalid provider list.");
    }
    return providers.map(normalizeProvider);
  },

  async listProviderConnections(signal) {
    const connections = await requestJson<unknown>("/provider-connections/", { signal });
    if (!Array.isArray(connections)) {
      throw new Error("Backend returned an invalid provider connection list.");
    }
    return connections.map(normalizeProviderConnection);
  },

  async listModels(connectionId, signal) {
    const response = await requestJson<unknown>(
      `/provider-connections/${encodeURIComponent(connectionId)}/models`,
      { signal },
    );
    if (!isRecord(response) || typeof response.provider !== "string" || !Array.isArray(response.models)) {
      throw new Error("Backend returned an invalid provider model list.");
    }
    const providerId = normalizeProviderId(response.provider);
    return response.models.map((model): ProviderModel => {
      if (!isRecord(model) || typeof model.id !== "string" || !model.id.trim()) {
        throw new Error("Backend returned an invalid provider model.");
      }
      return {
        id: model.id,
        name: typeof model.name === "string" ? model.name : undefined,
        providerId,
      };
    });
  },

  async connectProvider(input: ConnectProviderInput, signal?: AbortSignal) {
    const response = await requestJson<unknown>(`/api/providers/${encodeURIComponent(input.providerId)}/connect`, {
      method: "POST",
      signal,
      body: JSON.stringify({
        auth_method: input.authMethod,
        api_key: input.apiKey,
        account_label: input.accountLabel,
        server_url: input.serverUrl,
      }),
    });
    if (
      isRecord(response)
      && response.status === "connecting"
      && typeof response.provider === "string"
      && typeof response.attempt_id === "string"
      && typeof response.authorization_url === "string"
    ) {
      return {
        providerId: normalizeProviderId(response.provider),
        status: "connecting",
        attemptId: response.attempt_id,
        authorizationUrl: response.authorization_url,
      } satisfies ProviderAuthorization;
    }
    return normalizeProviderConnection(response);
  },

  async getOAuthConnectionStatus(providerId, attemptId, signal) {
    const response = await requestJson<unknown>(
      `/api/providers/${encodeURIComponent(providerId)}/oauth/status/${encodeURIComponent(attemptId)}`,
      { signal },
    );
    if (
      !isRecord(response)
      || typeof response.provider !== "string"
      || !["connecting", "connected", "error"].includes(String(response.status))
    ) {
      throw new Error("Backend returned an invalid OAuth status.");
    }
    return {
      providerId: normalizeProviderId(response.provider),
      status: response.status as OAuthConnectionStatus["status"],
      error: typeof response.error === "string" ? response.error : undefined,
    };
  },
};
