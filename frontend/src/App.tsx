import { useEffect, useMemo, useRef, useState } from "react";
import { SettingsModal } from "./components/settings/SettingsModal";
import { Sidebar } from "./components/Sidebar";
import { Workspace } from "./components/Workspace";
import { mockProjects } from "./data/mockProjects";
import { useProviders } from "./hooks/useProviders";
import { sendChatMessage } from "./services/api";
import { fetchProviderModels } from "./services/providers";
import type { Message, Project } from "./types";
import type { ProviderModel } from "./types/providers";
import { createId } from "./utils/ids";

function createMessage(role: Message["role"], content: string): Message {
  return {
    id: createId("message"),
    role,
    content,
    createdAt: new Date().toISOString(),
  };
}

function createProject(title = "Untitled project"): Project {
  const timestamp = new Date().toISOString();

  return {
    id: createId("project"),
    title,
    createdAt: timestamp,
    updatedAt: timestamp,
    messages: [],
  };
}

function titleFromMessage(message: string): string {
  const normalized = message.trim().replace(/\s+/g, " ");
  if (!normalized) {
    return "Untitled project";
  }

  return normalized.length > 42 ? `${normalized.slice(0, 42)}...` : normalized;
}

export default function App() {
  const [projects, setProjects] = useState<Project[]>(mockProjects);
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [sendingProjectId, setSendingProjectId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [models, setModels] = useState<ProviderModel[]>([]);
  const [selectedModelId, setSelectedModelId] = useState<string | null>(null);
  const [isModelsLoading, setIsModelsLoading] = useState(false);
  const [modelsError, setModelsError] = useState<string | null>(null);
  const isSendingRef = useRef(false);
  const providerState = useProviders();

  const selectedProject = useMemo(
    () => projects.find((project) => project.id === selectedProjectId) ?? null,
    [projects, selectedProjectId],
  );
  const ollamaConnection = providerState.providers.find(
    (provider) => provider.id === "ollama" && provider.status === "connected",
  )?.connection ?? null;

  useEffect(() => {
    if (!ollamaConnection) {
      setModels([]);
      setSelectedModelId(null);
      setModelsError(null);
      setIsModelsLoading(false);
      return;
    }

    const controller = new AbortController();
    const previousModelId = selectedModelId;
    setModels([]);
    setSelectedModelId(null);
    setIsModelsLoading(true);
    setModelsError(null);

    void fetchProviderModels(ollamaConnection.id, controller.signal)
      .then((nextModels) => {
        setModels(nextModels);
        setSelectedModelId(
          nextModels.some((model) => model.id === previousModelId)
            ? previousModelId
            : nextModels[0]?.id ?? null,
        );
      })
      .catch((loadError) => {
        if (loadError instanceof Error && loadError.name === "AbortError") {
          return;
        }
        setModels([]);
        setSelectedModelId(null);
        setModelsError(loadError instanceof Error ? loadError.message : "Could not load Ollama models.");
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setIsModelsLoading(false);
        }
      });

    return () => controller.abort();
  }, [ollamaConnection?.id, ollamaConnection?.endpointUrl, ollamaConnection?.updatedAt, providerState.refreshVersion]);

  const updateProjectMessages = (projectId: string, messages: Message[], title?: string) => {
    const timestamp = new Date().toISOString();

    setProjects((currentProjects) =>
      currentProjects.map((project) => {
        if (project.id !== projectId) {
          return project;
        }

        return {
          ...project,
          title: title ?? project.title,
          updatedAt: timestamp,
          messages: [...project.messages, ...messages],
        };
      }),
    );
  };

  const handleNewProject = () => {
    const project = createProject();
    setProjects((currentProjects) => [project, ...currentProjects]);
    setSelectedProjectId(project.id);
    setIsSettingsOpen(false);
    setError(null);
  };

  const handleSendMessage = async (content: string) => {
    const trimmedContent = content.trim();
    if (!trimmedContent || isSendingRef.current) {
      return;
    }
    if (!ollamaConnection || !selectedModelId || isModelsLoading) {
      setError("Connect Ollama and select an installed model before sending a message.");
      return;
    }

    isSendingRef.current = true;
    setError(null);
    setIsSending(true);

    let activeProject = selectedProject;
    if (!activeProject) {
      activeProject = createProject(titleFromMessage(trimmedContent));
      setProjects((currentProjects) => [activeProject as Project, ...currentProjects]);
      setSelectedProjectId(activeProject.id);
    }

    const userMessage = createMessage("user", trimmedContent);
    const shouldRenameProject = activeProject.title === "Untitled project" && activeProject.messages.length === 0;
    updateProjectMessages(
      activeProject.id,
      [userMessage],
      shouldRenameProject ? titleFromMessage(trimmedContent) : undefined,
    );
    setSendingProjectId(activeProject.id);

    try {
      const response = await sendChatMessage({
        connectionId: ollamaConnection.id,
        model: selectedModelId,
        messages: [...activeProject.messages, userMessage].map(({ role, content: messageContent }) => ({
          role,
          content: messageContent,
        })),
      });
      updateProjectMessages(activeProject.id, [createMessage("assistant", response.message)]);
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Could not reach the Python backend.",
      );
    } finally {
      isSendingRef.current = false;
      setIsSending(false);
      setSendingProjectId(null);
    }
  };

  return (
    <div className="app-shell">
      <Sidebar
        collapsed={sidebarCollapsed}
        projects={projects}
        selectedProjectId={selectedProjectId}
        settingsActive={isSettingsOpen}
        onNewProject={handleNewProject}
        onSelectProject={(projectId) => {
          setSelectedProjectId(projectId);
          setIsSettingsOpen(false);
          setError(null);
        }}
        onOpenSettings={() => {
          setIsSettingsOpen(true);
          setError(null);
        }}
        onToggleCollapsed={() => setSidebarCollapsed((collapsed) => !collapsed)}
      />
      <Workspace
        project={selectedProject}
        isSending={isSending}
        isThinking={isSending && sendingProjectId === selectedProject?.id}
        error={error}
        models={models}
        selectedModelId={selectedModelId}
        hasModelConnection={Boolean(ollamaConnection)}
        isModelsLoading={isModelsLoading}
        modelsError={modelsError}
        onSelectModel={setSelectedModelId}
        onSendMessage={handleSendMessage}
        onSelectPrompt={(prompt) => void handleSendMessage(prompt)}
      />
      {isSettingsOpen && (
        <SettingsModal providerState={providerState} onClose={() => setIsSettingsOpen(false)} />
      )}
    </div>
  );
}
