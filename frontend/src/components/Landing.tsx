import { useState } from "react";
import type { Project } from "../types";
import { NewChatIcon, SearchIcon, SettingsIcon } from "./ui/Icons";
import { AsciiQuill } from "./ui/AsciiQuill";

interface LandingProps {
  projects: Project[];
  isProjectsLoading: boolean;
  projectsError: string | null;
  error: string | null;
  onNewProject: () => void;
  onSelectProject: (projectId: string) => void;
  onOpenSettings: () => void;
}

// Past this many projects the menu gets a filter box.
const FILTER_THRESHOLD = 6;

function projectTime(project: Project): string {
  const date = new Date(project.updatedAt);
  const today = new Date();
  if (date.toDateString() === today.toDateString()) {
    return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  }
  return date.toLocaleDateString([], { month: "short", day: "numeric" });
}

export function Landing({
  projects,
  isProjectsLoading,
  projectsError,
  error,
  onNewProject,
  onSelectProject,
  onOpenSettings,
}: LandingProps) {
  const [query, setQuery] = useState("");
  const normalizedQuery = query.trim().toLowerCase();
  const visibleProjects = normalizedQuery
    ? projects.filter((project) => project.title.toLowerCase().includes(normalizedQuery))
    : projects;

  return (
    <main className="landing" data-dialog-fallback-focus tabIndex={-1}>
      {error && (
        <div className="error-banner" role="alert">
          <span>{error}</span>
        </div>
      )}

      <div className="landing-hero">
        <AsciiQuill className="hero-quill" />
        <h1 className="hero-headline">How can I help with your writing?</h1>
      </div>

      <section className="landing-menu" aria-labelledby="landing-menu-title">
        <header className="landing-menu-header">
          <h2 id="landing-menu-title">Recent projects</h2>
          {projects.length > FILTER_THRESHOLD && (
            <label className="landing-filter">
              <SearchIcon size={13} aria-hidden="true" />
              <input
                type="search"
                value={query}
                placeholder="Filter"
                aria-label="Filter projects"
                onChange={(event) => setQuery(event.target.value)}
              />
            </label>
          )}
        </header>

        <nav className="landing-projects" aria-label="Recent projects" aria-busy={isProjectsLoading}>
          {isProjectsLoading ? (
            <p className="landing-empty" role="status">Loading projects…</p>
          ) : projectsError ? (
            <p className="landing-empty" role="alert">{projectsError}</p>
          ) : projects.length === 0 ? (
            <p className="landing-empty">No projects yet. Create one to start writing.</p>
          ) : visibleProjects.length === 0 ? (
            <p className="landing-empty" role="status">No matching projects</p>
          ) : (
            visibleProjects.map((project) => (
              <button
                className="landing-project"
                key={project.id}
                type="button"
                title={project.path ?? project.title}
                onClick={() => onSelectProject(project.id)}
              >
                <span className="landing-project-title">{project.title}</span>
                {project.path && <span className="landing-project-path">{project.path}</span>}
                <span className="landing-project-time">{projectTime(project)}</span>
              </button>
            ))
          )}
        </nav>

        <button className="landing-new-project" type="button" onClick={onNewProject}>
          <NewChatIcon size={14} aria-hidden="true" />
          <span>New project</span>
        </button>
      </section>

      <button className="landing-settings" type="button" aria-label="Settings" title="Settings" onClick={onOpenSettings}>
        <SettingsIcon size={18} aria-hidden="true" />
      </button>
    </main>
  );
}
