import type { ChatRequest, CreateProjectInput, Project } from "../../types";
import type {
  ConnectProviderInput,
  OAuthConnectionStatus,
  ProviderAuthorization,
  ProviderConnection,
  ProviderModel,
  SupportedProvider,
} from "../../types/providers";

export type ChatStreamEvent =
  | { type: "delta"; content: string }
  | { type: "done" };

export interface CowriterApi {
  listProjects(signal?: AbortSignal): Promise<Project[]>;
  createProject(input: CreateProjectInput, signal?: AbortSignal): Promise<Project>;
  openProject(projectId: string, signal?: AbortSignal): Promise<void>;
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
