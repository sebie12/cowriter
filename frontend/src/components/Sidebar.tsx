import { useEffect, useRef, useState } from "react";
import cowriterPet from "../assets/icons/cowriter_pet.svg";
import type { Project } from "../types";
import { NewChatIcon, PanelIcon, SearchIcon, SettingsIcon } from "./ui/Icons";

interface SidebarProps {
  collapsed: boolean;
  projects: Project[];
  selectedProjectId: string | null;
  settingsActive: boolean;
  onNewProject: () => void;
  onSelectProject: (projectId: string) => void;
  onOpenSettings: () => void;
  onToggleCollapsed: () => void;
}

function projectTime(project: Project): string {
  const date = new Date(project.updatedAt);
  const today = new Date();
  if (date.toDateString() === today.toDateString()) {
    return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  }
  return date.toLocaleDateString([], { month: "short", day: "numeric" });
}

export function Sidebar({
  collapsed,
  projects,
  selectedProjectId,
  settingsActive,
  onNewProject,
  onSelectProject,
  onOpenSettings,
  onToggleCollapsed,
}: SidebarProps) {
  const [searchOpen, setSearchOpen] = useState(false);
  const [query, setQuery] = useState("");
  const searchRef = useRef<HTMLInputElement | null>(null);
  const visibleProjects = projects.filter((project) => project.title.toLowerCase().includes(query.trim().toLowerCase()));

  useEffect(() => {
    if (searchOpen && !collapsed) {
      searchRef.current?.focus();
    }
  }, [collapsed, searchOpen]);

  return (
    <aside className={`sidebar ${collapsed ? "collapsed" : ""}`}>
      <div className="sidebar-logo-row">
        {collapsed ? (
          <button className="rail-brand" type="button" onClick={onNewProject} aria-label="New project">
            <img src={cowriterPet} alt="" />
          </button>
        ) : (
          <button className="sidebar-brand" type="button" onClick={onNewProject} aria-label="New project">
            <span className="brand-mark"><img src={cowriterPet} alt="" /></span>
            <span className="brand-name">Cowriter</span>
          </button>
        )}
        <button
          className="sidebar-icon-button sidebar-toggle"
          type="button"
          onClick={onToggleCollapsed}
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          <PanelIcon size={collapsed ? 18 : 16} />
        </button>
      </div>

      <button className="new-project-button" type="button" onClick={onNewProject} title="New project">
        <NewChatIcon size={collapsed ? 18 : 14} />
        {!collapsed && <span>New project</span>}
      </button>

      <div className="sidebar-region">
        {collapsed ? (
          <button
            className="sidebar-icon-button rail-search"
            type="button"
            aria-label="Search projects"
            onClick={() => {
              onToggleCollapsed();
              setSearchOpen(true);
            }}
          >
            <SearchIcon size={18} />
          </button>
        ) : (
          <>
            <div className="sidebar-section-header">
              {!searchOpen && <span>Projects</span>}
              <div className={`sidebar-search ${searchOpen ? "open" : ""}`}>
                <button
                  type="button"
                  aria-label={searchOpen ? "Close project search" : "Search projects"}
                  onClick={() => {
                    setSearchOpen((current) => !current);
                    if (searchOpen) {
                      setQuery("");
                    }
                  }}
                >
                  <SearchIcon />
                </button>
                {searchOpen && (
                  <input
                    ref={searchRef}
                    value={query}
                    placeholder="Search projects"
                    aria-label="Search projects"
                    onChange={(event) => setQuery(event.target.value)}
                  />
                )}
              </div>
            </div>
            <nav className="project-list" aria-label="Projects">
              {visibleProjects.map((project) => (
                <button
                  className={`project-item ${project.id === selectedProjectId ? "active" : ""}`}
                  key={project.id}
                  type="button"
                  title={project.title}
                  onClick={() => onSelectProject(project.id)}
                >
                  <span className="project-dot" aria-hidden="true" />
                  <span className="project-title">{project.title}</span>
                  <span className="project-time">{projectTime(project)}</span>
                </button>
              ))}
              {visibleProjects.length === 0 && <p className="project-list-empty">No matching projects</p>}
            </nav>
          </>
        )}
      </div>

      <div className="sidebar-foot">
        <button
          className={`settings-trigger ${collapsed ? "rail" : ""} ${settingsActive ? "active" : ""}`}
          type="button"
          title="Settings"
          aria-current={settingsActive ? "page" : undefined}
          onClick={onOpenSettings}
        >
          <SettingsIcon size={collapsed ? 18 : 16} />
          {!collapsed && <span>Settings</span>}
        </button>
      </div>
    </aside>
  );
}
