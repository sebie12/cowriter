import { useReferences } from "../hooks/useReferences";
import { handleWindowDragMouseDown } from "../services/appWindow";
import type { CowriterApi } from "../services/backend/types";
import type { DraftDocument, Project } from "../types";
import type { ProviderModel } from "../types/providers";
import { ChatTab } from "./chat/ChatTab";
import type { ProviderOption } from "./composer/ModelSelector";
import type { ProjectView } from "./projectViews";
import { ResearchTab } from "./research/ResearchTab";
import { WorkTab, type ProofreadTarget } from "./work/WorkTab";

interface WorkspaceProps {
  api: CowriterApi;
  project: Project;
  activeView: ProjectView;
  isSending: boolean;
  isThinking: boolean;
  error: string | null;
  providers: ProviderOption[];
  activeProviderId: number | null;
  models: ProviderModel[];
  selectedModelId: string | null;
  isModelsLoading: boolean;
  modelsError: string | null;
  proofreadTarget: ProofreadTarget | null;
  onSelectProvider: (providerId: number) => void;
  onSelectModel: (modelId: string) => void;
  onSendMessage: (message: string) => void;
  onStopMessage: () => void;
  onDeleteChat: (projectId: string) => Promise<void>;
  onDraftChange: (projectId: string, draft: DraftDocument) => void;
  onOpenSettings: () => void;
}

export function Workspace({
  api,
  project,
  activeView,
  isSending,
  isThinking,
  error,
  providers,
  activeProviderId,
  models,
  selectedModelId,
  isModelsLoading,
  modelsError,
  proofreadTarget,
  onSelectProvider,
  onSelectModel,
  onSendMessage,
  onStopMessage,
  onDeleteChat,
  onDraftChange,
  onOpenSettings,
}: WorkspaceProps) {
  const references = useReferences(api, project.id);

  const composer = {
    onSend: onSendMessage,
    onStop: onStopMessage,
    isSending,
    canSend: Boolean(selectedModelId) && !isModelsLoading,
    providers,
    activeProviderId,
    models,
    selectedModelId,
    isModelsLoading,
    modelsError,
    onSelectProvider,
    onSelectModel,
    onOpenSettings,
  };

  return (
    <main className="workspace" data-phase="active" data-dialog-fallback-focus tabIndex={-1}>
      <header className="workspace-header" onMouseDown={handleWindowDragMouseDown}>
        <div className="workspace-title-row">
          <h1>{project.title}</h1>
        </div>
      </header>
      {error && (
        <div className="error-banner" role="alert">
          <span>{error}</span>
        </div>
      )}
      <>
          <WorkTab
            key={project.id}
            api={api}
            project={project}
            isActive={activeView === "work"}
            references={references}
            proofreadTarget={proofreadTarget}
            modelSelection={{
              providers,
              activeProviderId,
              models,
              selectedModelId,
              isModelsLoading,
              modelsError,
              onSelectProvider,
              onSelectModel,
              onOpenSettings,
            }}
            onDraftChange={onDraftChange}
          />
          <ResearchTab api={api} isActive={activeView === "research"} references={references} />
          <ChatTab
            project={project}
            isActive={activeView === "chat"}
            isThinking={isThinking}
            canDeleteChat={!isSending}
            onDeleteChat={() => onDeleteChat(project.id)}
            composer={composer}
          />
      </>
    </main>
  );
}
