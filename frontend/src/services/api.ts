import type { ChatRequest, ChatResponse } from "../types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:5000";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => null) as { error?: unknown } | null;
    throw new Error(
      typeof errorBody?.error === "string"
        ? errorBody.error
        : `Backend request failed with status ${response.status}`,
    );
  }

  return response.json() as Promise<T>;
}

export async function sendChatMessage(input: ChatRequest): Promise<ChatResponse> {
  const response = await request<unknown>("/api/chat", {
    method: "POST",
    body: JSON.stringify({
      connection_id: input.connectionId,
      provider: input.provider,
      model: input.model,
      message: input.message,
      system_prompt: input.systemPrompt,
      history: input.history ?? [],
    }),
  });

  if (
    typeof response !== "object"
    || response === null
    || !("message" in response)
    || typeof response.message !== "string"
  ) {
    throw new Error("Backend returned an invalid chat response.");
  }

  return { message: response.message };
}
