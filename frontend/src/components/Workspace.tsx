import { useEffect, useId, useLayoutEffect, useRef, useState } from "react";
import cowriterPet from "../assets/icons/cowriter_pet.svg";
import type { Project } from "../types";
import type { ProviderModel } from "../types/providers";
import { Composer } from "./composer/Composer";
import type { ProviderOption } from "./composer/ModelSelector";
import { Conversation } from "./Conversation";

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
  onSelectProvider: (providerId: number) => void;
  onSelectModel: (modelId: string) => void;
  onSendMessage: (message: string) => void;
  onStopMessage: () => void;
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
  onSelectProvider,
  onSelectModel,
  onSendMessage,
  onStopMessage,
}: WorkspaceProps) {
  const scrollRef = useRef<HTMLDivElement | null>(null);
  const scrollContentRef = useRef<HTMLDivElement | null>(null);
  const isNearBottomRef = useRef(true);
  const [isNearBottom, setIsNearBottom] = useState(true);
  const previousProjectIdRef = useRef<string | null>(null);
  const hero = project === null || project.messages.length === 0;

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
    if (isNearBottomRef.current) {
      scrollToBottom();
    }
  }, [project?.id, project?.messages, isThinking]);

  useEffect(() => {
    const scrollContainer = scrollRef.current;
    const scrollContent = scrollContentRef.current;
    if (!scrollContainer || !scrollContent) {
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
  }, [hero]);

  return (
    <main className="workspace" data-phase={hero ? "hero" : "active"}>
      {!hero && (
        <header className="workspace-header">
          <div className="workspace-title-row">
            <h1>{project.title}</h1>
          </div>
          <div className="workspace-tabs" role="tablist" aria-label="Project views">
            <button className="active" type="button" role="tab" aria-selected="true">Chat</button>
          </div>
        </header>
      )}
      {error && (
        <div className="error-banner" role="alert">
          Request failed. <span>{error}</span>
        </div>
      )}
      <div
        ref={scrollRef}
        className={`workspace-body ${hero ? "hero" : ""}`}
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
        {hero ? (
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
        ) : (
          <>
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
          </>
        )}
      </div>
    </main>
  );
}
