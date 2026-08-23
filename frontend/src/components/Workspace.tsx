import { useEffect, useLayoutEffect, useRef } from "react";
import type { Project } from "../types";
import type { ProviderModel } from "../types/providers";
import { Composer } from "./composer/Composer";
import { Conversation } from "./Conversation";

interface WorkspaceProps {
  project: Project | null;
  isSending: boolean;
  isThinking: boolean;
  error: string | null;
  providerName: string | null;
  models: ProviderModel[];
  selectedModelId: string | null;
  isModelsLoading: boolean;
  modelsError: string | null;
  onSelectModel: (modelId: string) => void;
  onSendMessage: (message: string) => void;
  onSelectPrompt: (prompt: string) => void;
}

const NEAR_BOTTOM_THRESHOLD = 96;

const starterPrompts = [
  "Start an essay about the social effects of printing technology",
  "Research a topic: AI agents in knowledge work",
  "Analyze sources for a literature review",
];

interface WorkspaceHeaderProps {
  project: Project | null;
  providerName: string | null;
  models: ProviderModel[];
  selectedModelId: string | null;
  isModelsLoading: boolean;
  modelsError: string | null;
  disabled: boolean;
  onSelectModel: (modelId: string) => void;
}

function WorkspaceHeader({
  project,
  providerName,
  models,
  selectedModelId,
  isModelsLoading,
  modelsError,
  disabled,
  onSelectModel,
}: WorkspaceHeaderProps) {
  const modelPlaceholder = !providerName
    ? "Choose provider in Settings"
    : isModelsLoading
      ? "Loading models..."
      : modelsError
        ? "Models unavailable"
        : "No models available";
  const modelStatus = modelsError
    ? `Could not load models: ${modelsError}`
    : isModelsLoading
      ? `Loading ${providerName ?? "provider"} models...`
      : providerName ?? "Select a provider in Settings.";

  return (
    <header className="workspace-header">
      <div>
        <p className="eyebrow">Writing workspace</p>
        <h1>{project ? project.title : "New research session"}</h1>
      </div>
      <div className="workspace-model-control">
        <label htmlFor="chat-model">Model</label>
        <select
          id="chat-model"
          value={selectedModelId ?? ""}
          disabled={disabled || isModelsLoading || !providerName || models.length === 0}
          title={modelsError ?? `Select a ${providerName ?? "chat"} model`}
          aria-describedby="chat-model-status"
          onChange={(event) => onSelectModel(event.target.value)}
        >
          {!selectedModelId && <option value="">{modelPlaceholder}</option>}
          {models.map((model) => (
            <option key={model.id} value={model.id}>{model.name ?? model.id}</option>
          ))}
        </select>
        <span id="chat-model-status" role="status" aria-live="polite">{modelStatus}</span>
      </div>
    </header>
  );
}

function EmptyState({ onSelectPrompt }: { onSelectPrompt: (prompt: string) => void }) {
  return (
    <section className="empty-state" aria-label="Start workspace">
      <p className="eyebrow">Draft, research, revise</p>
      <h2>What are you working on?</h2>
      <p>
        Start with a prompt, open a recent project, or create a new writing session with your selected model.
      </p>
      <div className="starter-actions">
        {starterPrompts.map((prompt) => (
          <button key={prompt} type="button" onClick={() => onSelectPrompt(prompt)}>
            {prompt.split(":")[0]}
          </button>
        ))}
      </div>
    </section>
  );
}

export function Workspace({
  project,
  isSending,
  isThinking,
  error,
  providerName,
  models,
  selectedModelId,
  isModelsLoading,
  modelsError,
  onSelectModel,
  onSendMessage,
  onSelectPrompt,
}: WorkspaceProps) {
  const scrollRef = useRef<HTMLDivElement | null>(null);
  const scrollContentRef = useRef<HTMLDivElement | null>(null);
  const isNearBottomRef = useRef(true);
  const previousProjectIdRef = useRef<string | null>(null);

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
  }, []);

  return (
    <main className="workspace">
      <WorkspaceHeader
        project={project}
        providerName={providerName}
        models={models}
        selectedModelId={selectedModelId}
        isModelsLoading={isModelsLoading}
        modelsError={modelsError}
        disabled={isSending}
        onSelectModel={onSelectModel}
      />
      {error && (
        <div className="error-banner" role="alert">
          Request failed. <span>{error}</span>
        </div>
      )}
      <div
        ref={scrollRef}
        className="workspace-body"
        onScroll={(event) => {
          const scrollContainer = event.currentTarget;
          const distanceFromBottom = scrollContainer.scrollHeight
            - scrollContainer.clientHeight
            - scrollContainer.scrollTop;
          isNearBottomRef.current = distanceFromBottom <= NEAR_BOTTOM_THRESHOLD;
        }}
      >
        <div ref={scrollContentRef} className="workspace-scroll-content">
          {project ? (
            <Conversation messages={project.messages} isSending={isThinking} />
          ) : (
            <EmptyState onSelectPrompt={onSelectPrompt} />
          )}
        </div>
      </div>
      <Composer
        onSend={onSendMessage}
        disabled={isSending}
        canSend={Boolean(selectedModelId) && !isModelsLoading}
      />
    </main>
  );
}
