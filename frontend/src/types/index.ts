export type MessageRole = "user" | "assistant";

export interface Message {
  id: string;
  role: MessageRole;
  content: string;
  createdAt: string;
}

export interface Project {
  id: string;
  title: string;
  createdAt: string;
  updatedAt: string;
  messages: Message[];
}

export interface ChatResponse {
  message: string;
}

export interface ChatRequest {
  connectionId: number;
  provider: string;
  model: string;
  message: string;
  systemPrompt?: string;
  history?: Array<Pick<Message, "role" | "content">>;
}
