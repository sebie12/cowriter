import type {
  ChatRequest,
  CreateProjectInput,
  DraftDocument,
  Paper,
  PaperSearchResult,
  Project,
  ProofreadIssue,
  ProofreadRequest,
  ProofreadResult,
  Reference,
  ToolCall,
} from "../../types";
import type {
  ConnectProviderInput,
  OAuthConnectionStatus,
  ProviderAuthorization,
  ProviderConnection,
  ProviderModel,
  SupportedProvider,
} from "../../types/providers";

export type ChatStreamEvent =
  | { type: "assistant_start"; messageId: string; createdAt: string }
  | { type: "assistant_delta"; messageId: string; content: string }
  | { type: "assistant_end"; messageId: string; finishedAt: string }
  | { type: "tool_call"; toolCall: ToolCall }
  | { type: "done" };

export interface CowriterApi {
  listProjects(signal?: AbortSignal): Promise<Project[]>;
  createProject(input: CreateProjectInput, signal?: AbortSignal): Promise<Project>;
  openProject(projectId: string, signal?: AbortSignal): Promise<void>;
  saveDraft(projectId: string, draft: DraftDocument | null, signal?: AbortSignal): Promise<void>;
  searchPapers(query: string, offset: number, signal?: AbortSignal): Promise<PaperSearchResult>;
  listReferences(projectId: string, signal?: AbortSignal): Promise<Reference[]>;
  saveReference(projectId: string, paper: Paper, signal?: AbortSignal): Promise<Reference>;
  deleteReference(projectId: string, referenceId: number, signal?: AbortSignal): Promise<void>;
  proofread(input: ProofreadRequest, signal?: AbortSignal): Promise<ProofreadResult>;
  streamChat(
    input: ChatRequest,
    onEvent: (event: ChatStreamEvent) => void,
    signal?: AbortSignal,
  ): Promise<void>;
  listProviders(signal?: AbortSignal): Promise<SupportedProvider[]>;
  listProviderConnections(signal?: AbortSignal): Promise<ProviderConnection[]>;
  listModels(connectionId: number, signal?: AbortSignal): Promise<ProviderModel[]>;
  connectProvider(
    input: ConnectProviderInput,
    signal?: AbortSignal,
  ): Promise<ProviderConnection | ProviderAuthorization>;
  getOAuthConnectionStatus(
    providerId: string,
    attemptId: string,
    signal?: AbortSignal,
  ): Promise<OAuthConnectionStatus>;
}
