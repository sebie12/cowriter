import type { Project } from "../types";
import { BackIcon, NewChatIcon, PanelIcon, SettingsIcon } from "./ui/Icons";
import { QuillMark } from "./ui/QuillMark";

interface SidebarProps {
  collapsed: boolean;
  project: Project;
  settingsActive: boolean;
  onNewProject: () => void;
  onClearActiveProject: () => void;
  onOpenSettings: () => void;
  onToggleCollapsed: () => void;
}

export function Sidebar({
  collapsed,
  project,
  settingsActive,
  onNewProject,
  onClearActiveProject,
  onOpenSettings,
  onToggleCollapsed,
}: SidebarProps) {
  return (
    <aside className={`sidebar ${collapsed ? "collapsed" : ""}`}>
      <div className="sidebar-logo-row">
        {collapsed ? (
          <button className="rail-brand" type="button" onClick={onNewProject} aria-label="New project">
            <QuillMark />
          </button>
        ) : (
          <button className="sidebar-brand" type="button" onClick={onNewProject} aria-label="New project">
            <span className="brand-mark"><QuillMark /></span>
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
            aria-label="Back to recent projects"
            title="Recent projects"
            onClick={onClearActiveProject}
          >
            <BackIcon size={18} />
          </button>
        ) : (
          <div className="active-project-sidebar">
            <button className="active-project-back" type="button" onClick={onClearActiveProject}>
              <BackIcon size={14} />
              <span>Recent projects</span>
            </button>
            <div className="active-project-heading">
              <h2 title={project.title}>{project.title}</h2>
              {project.path && <p title={project.path}>{project.path}</p>}
            </div>
          </div>
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
