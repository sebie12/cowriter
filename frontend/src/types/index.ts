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

/** TipTap/ProseMirror document JSON as stored by the backend. */
export interface DraftDocument {
  type: "doc";
  content?: unknown[];
  [key: string]: unknown;
}

export interface Project {
  id: string;
  title: string;
  path: string | null;
  writingContext: string | null;
  draft: DraftDocument | null;
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

export interface Paper {
  paperId: string;
  title: string;
  year: number | null;
  authors: string[];
  venue: string | null;
  abstract: string | null;
  tldr: string | null;
  citationCount: number | null;
  doi: string | null;
  url: string | null;
  pdfUrl: string | null;
}

export interface PaperSearchResult {
  total: number;
  offset: number;
  next: number | null;
  papers: Paper[];
}

export interface Reference extends Paper {
  id: number;
  createdAt: string;
}

export type ProofreadIssueType = "spelling" | "grammar" | "claim" | "style";

export interface ProofreadIssue {
  id: string;
  type: ProofreadIssueType;
  start: number;
  end: number;
  quote: string;
  explanation: string;
  suggestion: string | null;
  referenceIds: number[];
}

export interface ProofreadTopic {
  /** False when the draft has nothing to do with the essay's topic. */
  onTopic: boolean;
  explanation: string;
}

export interface ProofreadResult {
  issues: ProofreadIssue[];
  /** The model's verdict on whether the draft fits the essay's topic; null without an essay. */
  topic: ProofreadTopic | null;
  /** Project-relative path of the essay the draft was compared with, if any. */
  essayFile: string | null;
  essayTruncated: boolean;
}

export interface ProofreadRequest {
  projectId: string;
  connectionId: number;
  provider: string;
  model: string;
  text: string;
}
