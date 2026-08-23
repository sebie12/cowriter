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

const CHAT_PREFERENCES_KEY = "cowriter.chat-preferences.v1";

interface ChatPreferences {
  activeConnectionId: number | null;
  modelByConnectionId: Record<string, string>;
}

function loadChatPreferences(): ChatPreferences {
  try {
    const stored = JSON.parse(window.localStorage.getItem(CHAT_PREFERENCES_KEY) ?? "null") as unknown;
    if (typeof stored !== "object" || stored === null) {
      throw new Error("Invalid chat preferences.");
    }

    const candidate = stored as Partial<ChatPreferences>;
    const activeConnectionId = typeof candidate.activeConnectionId === "number"
      && Number.isInteger(candidate.activeConnectionId)
      && candidate.activeConnectionId > 0
      ? candidate.activeConnectionId
      : null;
    const modelByConnectionId = typeof candidate.modelByConnectionId === "object"
      && candidate.modelByConnectionId !== null
      ? Object.fromEntries(
        Object.entries(candidate.modelByConnectionId).filter(
          ([connectionId, modelId]) => /^\d+$/.test(connectionId) && typeof modelId === "string" && modelId.length > 0,
        ),
      )
      : {};

    return { activeConnectionId, modelByConnectionId };
  } catch {
    return { activeConnectionId: null, modelByConnectionId: {} };
  }
}

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
  const initialChatPreferencesRef = useRef<ChatPreferences | null>(null);
  if (initialChatPreferencesRef.current === null) {
    initialChatPreferencesRef.current = loadChatPreferences();
  }
  const initialChatPreferences = initialChatPreferencesRef.current;
  const [projects, setProjects] = useState<Project[]>(mockProjects);
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [sendingProjectId, setSendingProjectId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [models, setModels] = useState<ProviderModel[]>([]);
  const [activeConnectionId, setActiveConnectionId] = useState<number | null>(
    initialChatPreferences.activeConnectionId,
  );
  const [modelByConnectionId, setModelByConnectionId] = useState<Record<string, string>>(
    initialChatPreferences.modelByConnectionId,
  );
  const [modelsConnectionId, setModelsConnectionId] = useState<number | null>(null);
  const [isModelsLoading, setIsModelsLoading] = useState(false);
  const [modelsError, setModelsError] = useState<string | null>(null);
  const isSendingRef = useRef(false);
  const providerState = useProviders();

  const selectedProject = useMemo(
    () => projects.find((project) => project.id === selectedProjectId) ?? null,
    [projects, selectedProjectId],
  );
  const chatProviderIds = new Set(
    providerState.providers
      .filter((provider) => provider.chatSupported)
      .map((provider) => provider.id),
  );
  const connectedProviders = providerState.connections
    .filter((connection) => connection.status === "connected" && chatProviderIds.has(connection.providerId))
    .sort((firstConnection, secondConnection) => firstConnection.id - secondConnection.id);
  const activeConnection = providerState.connections.find(
    (connection) => connection.id === activeConnectionId
      && connectedProviders.some((candidate) => candidate.id === connection.id),
  ) ?? null;
  const preferredModelId = activeConnection
    ? modelByConnectionId[String(activeConnection.id)] ?? null
    : null;
  const selectedModelId = activeConnection
    && modelsConnectionId === activeConnection.id
    && models.some((model) => model.id === preferredModelId)
    ? preferredModelId
    : null;

  useEffect(() => {
    if (providerState.isLoading || providerState.isRefreshing || providerState.error) {
      return;
    }

    setActiveConnectionId((currentConnectionId) => (
      connectedProviders.some((connection) => connection.id === currentConnectionId)
        ? currentConnectionId
        : connectedProviders[0]?.id ?? null
    ));
  }, [
    providerState.isLoading,
    providerState.isRefreshing,
    providerState.error,
    providerState.providers,
    providerState.connections,
  ]);

  useEffect(() => {
    try {
      window.localStorage.setItem(CHAT_PREFERENCES_KEY, JSON.stringify({
        activeConnectionId,
        modelByConnectionId,
      } satisfies ChatPreferences));
    } catch {
      // Preferences remain available for the current session when storage is unavailable.
    }
  }, [activeConnectionId, modelByConnectionId]);

  useEffect(() => {
    if (!activeConnection) {
      setModels([]);
      setModelsConnectionId(null);
      setModelsError(null);
      setIsModelsLoading(false);
      return;
    }

    const controller = new AbortController();
    const connectionId = activeConnection.id;
    const previousModelId = modelByConnectionId[String(connectionId)] ?? null;
    setModels([]);
    setModelsConnectionId(null);
    setIsModelsLoading(true);
    setModelsError(null);

    void fetchProviderModels(connectionId, controller.signal)
      .then((nextModels) => {
        const nextModelId = nextModels.some((model) => model.id === previousModelId)
          ? previousModelId
          : nextModels[0]?.id ?? null;
        setModels(nextModels);
        setModelsConnectionId(connectionId);
        setModelByConnectionId((currentModels) => {
          if (nextModelId) {
            return { ...currentModels, [String(connectionId)]: nextModelId };
          }
          return currentModels;
        });
      })
      .catch((loadError) => {
        if (loadError instanceof Error && loadError.name === "AbortError") {
          return;
        }
        setModels([]);
        setModelsConnectionId(null);
        setModelsError(loadError instanceof Error ? loadError.message : "Could not load provider models.");
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setIsModelsLoading(false);
        }
      });

    return () => controller.abort();
  }, [activeConnection?.id, activeConnection?.endpointUrl, activeConnection?.updatedAt, providerState.refreshVersion]);

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
    if (!activeConnection || !selectedModelId || isModelsLoading) {
      setError("Connect a provider and select a model before sending a message.");
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
        connectionId: activeConnection.id,
        provider: activeConnection.providerId,
        model: selectedModelId,
        message: trimmedContent,
        history: activeProject.messages.map(({ role, content: messageContent }) => ({
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
        providerName={providerState.providers.find((provider) => provider.id === activeConnection?.providerId)?.name ?? null}
        models={models}
        selectedModelId={selectedModelId}
        isModelsLoading={isModelsLoading}
        modelsError={modelsError}
        onSelectModel={(modelId) => {
          if (!activeConnection || !models.some((model) => model.id === modelId)) {
            return;
          }
          setModelByConnectionId((currentModels) => ({
            ...currentModels,
            [String(activeConnection.id)]: modelId,
          }));
        }}
        onSendMessage={handleSendMessage}
        onSelectPrompt={(prompt) => void handleSendMessage(prompt)}
      />
      {isSettingsOpen && (
        <SettingsModal
          providerState={providerState}
          activeConnectionId={activeConnectionId}
          selectionDisabled={isSending}
          onSelectActiveConnection={(connectionId) => {
            setModels([]);
            setModelsConnectionId(null);
            setActiveConnectionId(connectionId);
          }}
          onClose={() => setIsSettingsOpen(false)}
        />
      )}
    </div>
  );
}
