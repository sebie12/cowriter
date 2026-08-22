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
  model: string;
  messages: Array<Pick<Message, "role" | "content">>;
}
