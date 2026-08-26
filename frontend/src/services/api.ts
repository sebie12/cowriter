import type { ChatRequest, ChatResponse } from "../types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:5000";

async function responseError(response: Response): Promise<Error> {
  const errorBody = await response.json().catch(() => null) as { error?: unknown } | null;
  return new Error(
    typeof errorBody?.error === "string"
      ? errorBody.error
      : `Backend request failed with status ${response.status}`,
  );
}

export async function sendChatMessage(
  input: ChatRequest,
  onChunk: (chunk: string) => void,
): Promise<ChatResponse> {
  const response = await fetch(`${API_BASE_URL}/api/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      connection_id: input.connectionId,
      provider: input.provider,
      model: input.model,
      message: input.message,
      system_prompt: input.systemPrompt,
      history: input.history ?? [],
    }),
  });

  if (!response.ok) {
    throw await responseError(response);
  }
  if (!response.body) {
    throw new Error("Backend returned an unreadable chat stream.");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let message = "";
  let finished = false;

  const processLine = (line: string) => {
    if (!line.trim()) {
      return;
    }

    let event: unknown;
    try {
      event = JSON.parse(line);
    } catch {
      throw new Error("Backend returned an invalid chat stream.");
    }

    if (typeof event !== "object" || event === null || !("type" in event)) {
      throw new Error("Backend returned an invalid chat stream.");
    }
    if (event.type === "delta" && "content" in event && typeof event.content === "string") {
      message += event.content;
      onChunk(event.content);
      return;
    }
    if (event.type === "done") {
      finished = true;
      return;
    }
    if (event.type === "error" && "error" in event && typeof event.error === "string") {
      throw new Error(event.error);
    }
    throw new Error("Backend returned an invalid chat stream.");
  };

  try {
    while (!finished) {
      const { value, done } = await reader.read();
      buffer += decoder.decode(value, { stream: !done });

      let newlineIndex = buffer.indexOf("\n");
      while (newlineIndex >= 0) {
        processLine(buffer.slice(0, newlineIndex));
        buffer = buffer.slice(newlineIndex + 1);
        if (finished) {
          break;
        }
        newlineIndex = buffer.indexOf("\n");
      }

      if (done) {
        if (!finished && buffer.trim()) {
          processLine(buffer);
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
  return { message };
}
