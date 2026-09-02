import { useEffect, useId, useLayoutEffect, useRef, useState } from "react";
import cowriterPet from "../assets/icons/cowriter_pet.svg";
import type { ProjectFilesystemService } from "../services/projectFilesystem";
import type { Project } from "../types";
import type { ProviderModel } from "../types/providers";
import { Composer } from "./composer/Composer";
import type { ProviderOption } from "./composer/ModelSelector";
import { Conversation } from "./Conversation";
import { ProjectSourceEditor } from "./projects/ProjectSourceEditor";
import { WritingEditor } from "./WritingEditor";

type ProjectView = "chat" | "writing" | "source";

interface WorkspaceProps {
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
  filesystemService: ProjectFilesystemService;
  onSelectProvider: (providerId: number) => void;
  onSelectModel: (modelId: string) => void;
  onSendMessage: (message: string) => void;
  onStopMessage: () => void;
  onWritingContentChange: (projectId: string, content: string) => void;
}

const NEAR_BOTTOM_THRESHOLD = 96;

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
  filesystemService,
  onSelectProvider,
  onSelectModel,
  onSendMessage,
  onStopMessage,
  onWritingContentChange,
}: WorkspaceProps) {
  const scrollRef = useRef<HTMLDivElement | null>(null);
  const scrollContentRef = useRef<HTMLDivElement | null>(null);
  const isNearBottomRef = useRef(true);
  const [isNearBottom, setIsNearBottom] = useState(true);
  const [activeView, setActiveView] = useState<ProjectView>("chat");
  const previousProjectIdRef = useRef<string | null>(null);
  const hero = project === null;

  const scrollToBottom = () => {
    const scrollContainer = scrollRef.current;
    if (scrollContainer) {
      scrollContainer.scrollTop = scrollContainer.scrollHeight;
    }
  };

  useLayoutEffect(() => {
    const projectId = project?.id ?? null;
    if (projectId !== previousProjectIdRef.current) {
      previousProjectIdRef.current = projectId;
      isNearBottomRef.current = true;
      setIsNearBottom(true);
    }
    if (activeView === "chat" && isNearBottomRef.current) {
      scrollToBottom();
    }
  }, [activeView, project?.id, project?.messages, isThinking]);

  useEffect(() => {
    setActiveView("chat");
  }, [project?.id]);

  useEffect(() => {
    const scrollContainer = scrollRef.current;
    const scrollContent = scrollContentRef.current;
    if (activeView !== "chat" || !scrollContainer || !scrollContent) {
      return;
    }

    const observer = new ResizeObserver(() => {
      if (isNearBottomRef.current) {
        scrollToBottom();
      }
    });
    observer.observe(scrollContainer);
    observer.observe(scrollContent);
    return () => observer.disconnect();
  }, [activeView, hero]);

  return (
    <main className="workspace" data-phase={hero ? "hero" : "active"}>
      {!hero && (
        <header className="workspace-header">
          <div className="workspace-title-row">
            <h1>{project.title}</h1>
            <div className="workspace-tabs" role="tablist" aria-label="Project views">
              <button
                id="project-chat-tab"
                className={activeView === "chat" ? "active" : ""}
                type="button"
                role="tab"
                aria-controls="project-chat-panel"
                aria-selected={activeView === "chat"}
                onClick={() => setActiveView("chat")}
              >
                Chat
              </button>
              <button
                id="project-writing-tab"
                className={activeView === "writing" ? "active" : ""}
                type="button"
                role="tab"
                aria-controls="project-writing-panel"
                aria-selected={activeView === "writing"}
                onClick={() => setActiveView("writing")}
              >
                Writing
              </button>
              <button
                id="project-source-tab"
                className={activeView === "source" ? "active" : ""}
                type="button"
                role="tab"
                aria-controls="project-source-panel"
                aria-selected={activeView === "source"}
                onClick={() => setActiveView("source")}
              >
                Source
              </button>
            </div>
          </div>
          <div className="file-tabs" />
        </header>
      )}
      {error && (hero || activeView === "chat") && (
        <div className="error-banner" role="alert">
          <span>{error}</span>
        </div>
      )}
      {hero ? (
        <div className="workspace-body hero">
          <div className="hero-stage">
            <div className="hero-stack">
              <div className="hero-headline">
                <span className="hero-mark"><img src={cowriterPet} alt="" /></span>
                <span>How can I help with your writing?</span>
              </div>
              <div className="hero-composer">
                <HeroGlow />
                <Composer
                  hero
                  onSend={onSendMessage}
                  onStop={onStopMessage}
                  isSending={isSending}
                  canSend={Boolean(selectedModelId) && !isModelsLoading}
                  providers={providers}
                  activeProviderId={activeProviderId}
                  models={models}
                  selectedModelId={selectedModelId}
                  isModelsLoading={isModelsLoading}
                  modelsError={modelsError}
                  onSelectProvider={onSelectProvider}
                  onSelectModel={onSelectModel}
                />
              </div>
            </div>
          </div>
        </div>
      ) : (
        <>
          <div
            id="project-chat-panel"
            ref={scrollRef}
            className="workspace-body"
            role="tabpanel"
            aria-labelledby="project-chat-tab"
            hidden={activeView !== "chat"}
            data-conversation-scroll
            onScroll={(event) => {
              const scrollContainer = event.currentTarget;
              const distanceFromBottom = scrollContainer.scrollHeight
                - scrollContainer.clientHeight
                - scrollContainer.scrollTop;
              isNearBottomRef.current = distanceFromBottom <= NEAR_BOTTOM_THRESHOLD;
              setIsNearBottom(isNearBottomRef.current);
            }}
          >
            <div ref={scrollContentRef} className="workspace-scroll-content">
              <Conversation messages={project.messages} isSending={isThinking} />
            </div>
            {!isNearBottom && (
              <div className="scroll-to-bottom-slot">
                <button
                  className="scroll-to-bottom"
                  type="button"
                  aria-label="Jump to latest message"
                  onClick={() => {
                    isNearBottomRef.current = true;
                    setIsNearBottom(true);
                    scrollToBottom();
                  }}
                >
                  <span aria-hidden="true">↓</span>
                </button>
              </div>
            )}
            <div className="composer-seat">
              <Composer
                hero={false}
                onSend={onSendMessage}
                onStop={onStopMessage}
                isSending={isSending}
                canSend={Boolean(selectedModelId) && !isModelsLoading}
                providers={providers}
                activeProviderId={activeProviderId}
                models={models}
                selectedModelId={selectedModelId}
                isModelsLoading={isModelsLoading}
                modelsError={modelsError}
                onSelectProvider={onSelectProvider}
                onSelectModel={onSelectModel}
              />
            </div>
          </div>
          <div
            id="project-writing-panel"
            className="workspace-body writing-body"
            role="tabpanel"
            aria-labelledby="project-writing-tab"
            hidden={activeView !== "writing"}
          >
            <WritingEditor
              key={project.id}
              content={project.writingContent}
              onChange={(content) => onWritingContentChange(project.id, content)}
            />
          </div>
          <div
            id="project-source-panel"
            className="workspace-body source-body"
            role="tabpanel"
            aria-labelledby="project-source-tab"
            hidden={activeView !== "source"}
          >
            <ProjectSourceEditor
              key={project.id}
              project={project}
              filesystemService={filesystemService}
            />
          </div>
        </>
      )}
    </main>
  );
}
