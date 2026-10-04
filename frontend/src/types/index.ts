export type MessageRole = "user" | "assistant";

export interface Message {
  kind: "message";
  id: string;
  role: MessageRole;
  content: string;
  createdAt: string;
  status?: "streaming" | "complete" | "stopped" | "error";
}

export type ToolCallStatus = "pending" | "running" | "completed" | "failed";

export interface ToolCall {
  kind: "tool-call";
  id: string;
  providerCallId: string | null;
  toolName: string;
  input: unknown;
  output: unknown | null;
  status: ToolCallStatus;
  error: string | null;
  calledAt: string;
  finishedAt: string | null;
}

export type ConversationItem = Message | ToolCall;

export interface Project {
  id: string;
  title: string;
  path: string | null;
  writingContext: string | null;
  writingContent: string;
  createdAt: string;
  updatedAt: string;
  conversationItems: ConversationItem[];
}

export interface CreateProjectInput {
  name: string;
  writingContext: {
    tone: string;
    writingStyle: string;
    academicLevel: string;
    language: string;
    essayType: string;
    additionalInstructions?: string;
  } | null;
  path: string | null;
}

export interface ProjectFileEntry {
  name: string;
  kind: "file" | "directory";
}

export interface ProjectSourceFile {
  name: string;
  relativePath: string;
}

export interface ChatRequest {
  projectId: string;
  connectionId: number;
  provider: string;
  model: string;
  message: string;
  projectTitle?: string;
  projectDescription?: string;
  systemPrompt?: string;
  history?: Array<Pick<Message, "role" | "content">>;
}
