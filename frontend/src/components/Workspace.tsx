import { useEffect, useId, useRef, useState } from "react";
import cowriterPet from "../assets/icons/cowriter_pet.svg";
import { useReferences } from "../hooks/useReferences";
import type { CowriterApi } from "../services/backend/types";
import type { DraftDocument, Project } from "../types";
import type { ProviderModel } from "../types/providers";
import { ChatTab } from "./chat/ChatTab";
import { Composer } from "./composer/Composer";
import type { ProviderOption } from "./composer/ModelSelector";
import { ResearchTab } from "./research/ResearchTab";
import { WorkTab, type ProofreadTarget } from "./work/WorkTab";

type ProjectView = "work" | "research" | "chat";

interface WorkspaceProps {
  api: CowriterApi;
  project: Project | null;
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
  onDraftChange: (projectId: string, draft: DraftDocument) => void;
  onOpenSettings: () => void;
}

const PROJECT_VIEWS: Array<{ id: ProjectView; label: string }> = [
  { id: "work", label: "Work" },
  { id: "research", label: "Research" },
  { id: "chat", label: "Chat" },
];

function HeroGlow() {
  const filterId = `cowriter-hero-glow-${useId().replace(/:/g, "")}`;
  return (
    <svg className="hero-glow" viewBox="0 0 1051 468" fill="none" aria-hidden="true">
      <defs>
        <filter id={filterId} x="0" y="0" width="1051" height="468" filterUnits="userSpaceOnUse">
          <feGaussianBlur stdDeviation="50" />
        </filter>
      </defs>
      <g filter={`url(#${filterId})`}>
        <ellipse cx="525.5" cy="234" rx="425.5" ry="134" fill="#6187D8" fillOpacity="0.09" />
      </g>
    </svg>
  );
}

export function Workspace({
  api,
  project,
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
  onDraftChange,
  onOpenSettings,
}: WorkspaceProps) {
  const [activeView, setActiveView] = useState<ProjectView>("work");
  const tabRefs = useRef<Array<HTMLButtonElement | null>>([]);
  const references = useReferences(api, project?.id ?? null);
  const hero = project === null;

  useEffect(() => {
    setActiveView("work");
  }, [project?.id]);

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
    <main className="workspace" data-phase={hero ? "hero" : "active"} data-dialog-fallback-focus tabIndex={-1}>
      {!hero && (
        <header className="workspace-header">
          <div className="workspace-title-row">
            <h1>{project.title}</h1>
            <div className="workspace-tabs" role="tablist" aria-label="Project views">
              {PROJECT_VIEWS.map((view, index) => (
                <button
                  ref={(element) => { tabRefs.current[index] = element; }}
                  id={`project-${view.id}-tab`}
                  className={activeView === view.id ? "active" : ""}
                  type="button"
                  role="tab"
                  tabIndex={activeView === view.id ? 0 : -1}
                  aria-controls={`project-${view.id}-panel`}
                  aria-selected={activeView === view.id}
                  key={view.id}
                  onClick={() => setActiveView(view.id)}
                  onKeyDown={(event) => {
                    if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) {
                      return;
                    }
                    event.preventDefault();
                    const nextIndex = event.key === "Home"
                      ? 0
                      : event.key === "End"
                        ? PROJECT_VIEWS.length - 1
                        : event.key === "ArrowLeft"
                          ? (index - 1 + PROJECT_VIEWS.length) % PROJECT_VIEWS.length
                          : (index + 1) % PROJECT_VIEWS.length;
                    setActiveView(PROJECT_VIEWS[nextIndex].id);
                    tabRefs.current[nextIndex]?.focus();
                  }}
                >
                  {view.label}
                </button>
              ))}
            </div>
          </div>
          <div className="file-tabs" />
        </header>
      )}
      {error && (
        <div className="error-banner" role="alert">
          <span>{error}</span>
        </div>
      )}
      {hero ? (
        <div className="workspace-body hero">
          <div className="hero-stage">
            <div className="hero-stack">
              <h1 className="hero-headline">
                <span className="hero-mark"><img src={cowriterPet} alt="" /></span>
                <span>How can I help with your writing?</span>
              </h1>
              <div className="hero-composer">
                <HeroGlow />
                <Composer hero {...composer} />
              </div>
            </div>
          </div>
        </div>
      ) : (
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
            composer={composer}
          />
        </>
      )}
    </main>
  );
}
