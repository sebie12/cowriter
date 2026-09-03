import { useEffect, useMemo, useRef, useState } from "react";
import { ProjectModal } from "./components/projects/ProjectModal";
import { SettingsModal } from "./components/settings/SettingsModal";
import { Sidebar } from "./components/Sidebar";
import { Workspace } from "./components/Workspace";
import { useProviders } from "./hooks/useProviders";
import { projectFilesystemService } from "./services/projectFilesystem";
import type { CowriterApi } from "./services/backend/types";
import type { CreateProjectInput, Message, Project } from "./types";
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

function createMessage(
  role: Message["role"],
  content: string,
  status: Message["status"] = "complete",
): Message {
  return {
    id: createId("message"),
    role,
    content,
    createdAt: new Date().toISOString(),
    status,
  };
}

function titleFromMessage(message: string): string {
  const normalized = message.trim().replace(/\s+/g, " ");
  if (!normalized) {
    return "Untitled project";
  }

  return normalized.length > 42 ? `${normalized.slice(0, 42)}...` : normalized;
}

export default function App({ api }: { api: CowriterApi }) {
  const initialChatPreferencesRef = useRef<ChatPreferences | null>(null);
  if (initialChatPreferencesRef.current === null) {
    initialChatPreferencesRef.current = loadChatPreferences();
  }
  const initialChatPreferences = initialChatPreferencesRef.current;
  const [projects, setProjects] = useState<Project[]>([]);
  const [isProjectsLoading, setIsProjectsLoading] = useState(true);
  const [projectsError, setProjectsError] = useState<string | null>(null);
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [isProjectModalOpen, setIsProjectModalOpen] = useState(false);
  const [pendingProjectMessage, setPendingProjectMessage] = useState<string | null>(null);
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
  const chatControllerRef = useRef<AbortController | null>(null);
  const providerState = useProviders(api);

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
    const controller = new AbortController();

    void api.listProjects(controller.signal)
      .then((loadedProjects) => {
        setProjects(loadedProjects);
        setProjectsError(null);
      })
      .catch((loadError) => {
        if (loadError instanceof Error && loadError.name === "AbortError") {
          return;
        }
        setProjectsError(loadError instanceof Error ? loadError.message : "Could not load projects.");
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setIsProjectsLoading(false);
        }
      });

    return () => controller.abort();
  }, [api]);

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

    void api.listModels(connectionId, controller.signal)
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
  }, [api, activeConnection?.id, activeConnection?.endpointUrl, activeConnection?.updatedAt, providerState.refreshVersion]);

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

  const appendToProjectMessage = (projectId: string, messageId: string, content: string) => {
    const timestamp = new Date().toISOString();

    setProjects((currentProjects) =>
      currentProjects.map((project) => project.id === projectId
        ? {
            ...project,
            updatedAt: timestamp,
            messages: project.messages.map((message) => message.id === messageId
              ? { ...message, content: message.content + content }
              : message),
          }
        : project),
    );
  };

  const updateProjectMessageStatus = (
    projectId: string,
    messageId: string,
    status: NonNullable<Message["status"]>,
  ) => {
    const timestamp = new Date().toISOString();
    setProjects((currentProjects) => currentProjects.map((project) => project.id === projectId
      ? {
          ...project,
          updatedAt: timestamp,
          messages: project.messages.map((message) => message.id === messageId
            ? { ...message, status }
            : message),
        }
      : project));
  };

  const sendMessageToProject = async (activeProject: Project, trimmedContent: string) => {
    if (!activeConnection || !selectedModelId || isModelsLoading) {
      setError("Connect a provider and select a model before sending a message.");
      return;
    }

    isSendingRef.current = true;
    setError(null);
    setIsSending(true);

    const userMessage = createMessage("user", trimmedContent);
    const assistantMessage = createMessage("assistant", "", "streaming");
    const shouldRenameProject = activeProject.title === "Untitled project" && activeProject.messages.length === 0;
    updateProjectMessages(
      activeProject.id,
      [userMessage, assistantMessage],
      shouldRenameProject ? titleFromMessage(trimmedContent) : undefined,
    );
    setSendingProjectId(activeProject.id);
    const controller = new AbortController();
    chatControllerRef.current = controller;

    try {
      await api.streamChat(
        {
          projectId: activeProject.id,
          connectionId: activeConnection.id,
          provider: activeConnection.providerId,
          model: selectedModelId,
          message: trimmedContent,
          projectTitle: activeProject.title,
          projectDescription: activeProject.writingContext ?? undefined,
          history: activeProject.messages
            .filter((message) => message.content.trim().length > 0)
            .map(({ role, content: messageContent }) => ({
              role,
              content: messageContent,
            })),
        },
        (event) => {
          if (event.type === "delta") {
            appendToProjectMessage(activeProject.id, assistantMessage.id, event.content);
          } else {
            updateProjectMessageStatus(activeProject.id, assistantMessage.id, "complete");
          }
        },
        controller.signal,
      );
    } catch (requestError) {
      if (requestError instanceof Error && requestError.name === "AbortError") {
        updateProjectMessageStatus(activeProject.id, assistantMessage.id, "stopped");
        return;
      }
      updateProjectMessageStatus(activeProject.id, assistantMessage.id, "error");
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Could not reach the Python backend.",
      );
    } finally {
      if (chatControllerRef.current === controller) {
        chatControllerRef.current = null;
      }
      isSendingRef.current = false;
      setIsSending(false);
      setSendingProjectId(null);
    }
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
    if (!selectedProject) {
      setPendingProjectMessage(trimmedContent);
      setIsSettingsOpen(false);
      setIsProjectModalOpen(true);
      setError(null);
      return;
    }
    await sendMessageToProject(selectedProject, trimmedContent);
  };

  const handleCreateProject = async (input: CreateProjectInput) => {
    const project = await api.createProject(input);
    setProjects((currentProjects) => [project, ...currentProjects]);
    setProjectsError(null);
    setSelectedProjectId(project.id);
    setIsSettingsOpen(false);
    setError(null);

    const initialMessage = pendingProjectMessage;
    setPendingProjectMessage(null);
    if (initialMessage) {
      void sendMessageToProject(project, initialMessage);
    }
  };

  const handleSelectProject = (projectId: string) => {
    setSelectedProjectId(projectId);
    setIsSettingsOpen(false);
    setIsProjectModalOpen(false);
    setError(null);

    void api.openProject(projectId).catch((openError) => {
      setError(openError instanceof Error ? openError.message : "Could not update the project's last-opened time.");
    });
  };

  const handleStopMessage = () => {
    chatControllerRef.current?.abort();
  };

  useEffect(() => () => chatControllerRef.current?.abort(), []);

  const handleWritingContentChange = (projectId: string, writingContent: string) => {
    setProjects((currentProjects) => currentProjects.map((project) => {
      if (project.id !== projectId || project.writingContent === writingContent) {
        return project;
      }
      return {
        ...project,
        writingContent,
        updatedAt: new Date().toISOString(),
      };
    }));
  };

  return (
    <div className="app-shell">
      <Sidebar
        collapsed={sidebarCollapsed}
        projects={projects}
        isProjectsLoading={isProjectsLoading}
        projectsError={projectsError}
        selectedProjectId={selectedProjectId}
        settingsActive={isSettingsOpen}
        activeProject={selectedProject}
        filesystemService={projectFilesystemService}
        onNewProject={() => {
          setPendingProjectMessage(null);
          setIsSettingsOpen(false);
          setIsProjectModalOpen(true);
          setError(null);
        }}
        onSelectProject={handleSelectProject}
        onClearActiveProject={() => {
          setSelectedProjectId(null);
          setError(null);
        }}
        onOpenSettings={() => {
          setIsSettingsOpen(true);
          setIsProjectModalOpen(false);
          setPendingProjectMessage(null);
          setError(null);
        }}
        onToggleCollapsed={() => setSidebarCollapsed((collapsed) => !collapsed)}
      />
      <Workspace
        project={selectedProject}
        isSending={isSending}
        isThinking={isSending && sendingProjectId === selectedProject?.id}
        error={error}
        providers={connectedProviders.map((connection) => ({
          id: connection.id,
          name: providerState.providers.find((provider) => provider.id === connection.providerId)?.name ?? connection.providerId,
          detail: connection.accountLabel,
        }))}
        activeProviderId={activeConnectionId}
        models={models}
        selectedModelId={selectedModelId}
        isModelsLoading={isModelsLoading}
        modelsError={modelsError}
        filesystemService={projectFilesystemService}
        onSelectProvider={(connectionId) => {
          setModels([]);
          setModelsConnectionId(null);
          setActiveConnectionId(connectionId);
        }}
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
        onStopMessage={handleStopMessage}
        onWritingContentChange={handleWritingContentChange}
      />
      {isProjectModalOpen && (
        <ProjectModal
          filesystemService={projectFilesystemService}
          initialName={pendingProjectMessage ? titleFromMessage(pendingProjectMessage) : undefined}
          onCreateProject={handleCreateProject}
          onClose={() => {
            setIsProjectModalOpen(false);
            setPendingProjectMessage(null);
          }}
        />
      )}
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
