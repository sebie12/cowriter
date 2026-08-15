import { useMemo, useState } from "react";
import { Sidebar } from "./components/Sidebar";
import { Workspace } from "./components/Workspace";
import { mockProjects } from "./data/mockProjects";
import { sendChatMessage } from "./services/api";
import type { Message, Project } from "./types";
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
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const selectedProject = useMemo(
    () => projects.find((project) => project.id === selectedProjectId) ?? null,
    [projects, selectedProjectId],
  );

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
    setError(null);
  };

  const handleSendMessage = async (content: string) => {
    const trimmedContent = content.trim();
    if (!trimmedContent || isSending) {
      return;
    }

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

    try {
      const response = await sendChatMessage(trimmedContent);
      updateProjectMessages(activeProject.id, [createMessage("assistant", response.message)]);
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Could not reach the Python backend.",
      );
    } finally {
      setIsSending(false);
    }
  };

  return (
    <div className="app-shell">
      <Sidebar
        collapsed={sidebarCollapsed}
        projects={projects}
        selectedProjectId={selectedProjectId}
        onNewProject={handleNewProject}
        onSelectProject={(projectId) => {
          setSelectedProjectId(projectId);
          setError(null);
        }}
        onToggleCollapsed={() => setSidebarCollapsed((collapsed) => !collapsed)}
      />
      <Workspace
        project={selectedProject}
        isSending={isSending}
        error={error}
        onSendMessage={handleSendMessage}
        onSelectPrompt={(prompt) => void handleSendMessage(prompt)}
      />
    </div>
  );
}
