const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:5000";

async function responseError(response: Response): Promise<Error> {
  const errorBody = await response.json().catch(() => null) as { error?: unknown } | null;
  return new Error(
    typeof errorBody?.error === "string"
      ? errorBody.error
      : `Backend request failed with status ${response.status}.`,
  );
}

export async function request(path: string, options?: RequestInit): Promise<Response> {
  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...options?.headers,
      },
    });
    if (!response.ok) {
      throw await responseError(response);
    }
    return response;
  } catch (error) {
    if (error instanceof Error && error.name === "AbortError") {
      throw error;
    }
    if (error instanceof TypeError) {
      throw new Error("Could not reach the Cowriter backend.");
    }
    throw error;
  }
}

export async function requestJson<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await request(path, options);
  return response.json() as Promise<T>;
}
