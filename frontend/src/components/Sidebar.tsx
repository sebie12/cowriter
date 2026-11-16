import { useRef, type ReactNode } from "react";
import type { Project } from "../types";
import { displayPath } from "../utils/paths";
import { PROJECT_VIEWS, type ProjectView } from "./projectViews";
import { BackIcon, ChatIcon, NewChatIcon, PanelIcon, PenIcon, SearchIcon, SettingsIcon } from "./ui/Icons";
import { QuillMark } from "./ui/QuillMark";

const VIEW_ICONS: Record<ProjectView, (size: number) => ReactNode> = {
  work: (size) => <PenIcon size={size} />,
  research: (size) => <SearchIcon size={size} />,
  chat: (size) => <ChatIcon size={size} />,
};

interface SidebarProps {
  collapsed: boolean;
  project: Project;
  activeView: ProjectView;
  settingsActive: boolean;
  onNewProject: () => void;
  onClearActiveProject: () => void;
  onOpenSettings: () => void;
  onSelectView: (view: ProjectView) => void;
  onToggleCollapsed: () => void;
}

export function Sidebar({
  collapsed,
  project,
  activeView,
  settingsActive,
  onNewProject,
  onClearActiveProject,
  onOpenSettings,
  onSelectView,
  onToggleCollapsed,
}: SidebarProps) {
  const viewRefs = useRef<Array<HTMLButtonElement | null>>([]);
  const iconSize = collapsed ? 18 : 15;

  const viewNav = (
    <div
      className={`project-view-nav ${collapsed ? "rail" : ""}`}
      role="tablist"
      aria-label="Project views"
      aria-orientation="vertical"
    >
      {PROJECT_VIEWS.map((view, index) => {
        const isActive = activeView === view.id;
        return (
          <button
            ref={(element) => { viewRefs.current[index] = element; }}
            id={`project-${view.id}-tab`}
            className={isActive ? "active" : ""}
            type="button"
            role="tab"
            title={collapsed ? view.label : undefined}
            aria-label={collapsed ? view.label : undefined}
            tabIndex={isActive ? 0 : -1}
            aria-controls={`project-${view.id}-panel`}
            aria-selected={isActive}
            key={view.id}
            onClick={() => onSelectView(view.id)}
            onKeyDown={(event) => {
              if (!["ArrowUp", "ArrowDown", "Home", "End"].includes(event.key)) {
                return;
              }
              event.preventDefault();
              const count = PROJECT_VIEWS.length;
              const nextIndex = event.key === "Home"
                ? 0
                : event.key === "End"
                  ? count - 1
                  : event.key === "ArrowUp"
                    ? (index - 1 + count) % count
                    : (index + 1) % count;
              onSelectView(PROJECT_VIEWS[nextIndex].id);
              viewRefs.current[nextIndex]?.focus();
            }}
          >
            {VIEW_ICONS[view.id](iconSize)}
            {!collapsed && <span>{view.label}</span>}
          </button>
        );
      })}
    </div>
  );
  return (
    <aside className={`sidebar ${collapsed ? "collapsed" : ""}`}>
      <div className="sidebar-logo-row">
        {collapsed ? (
          <button className="rail-brand" type="button" onClick={onNewProject} aria-label="New project">
            <QuillMark />
          </button>
        ) : (
          <button className="sidebar-brand" type="button" onClick={onNewProject} aria-label="New project">
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
          <>
            <button
              className="sidebar-icon-button rail-search"
              type="button"
              aria-label="Back to recent projects"
              title="Recent projects"
              onClick={onClearActiveProject}
            >
              <BackIcon size={18} />
            </button>
            {viewNav}
          </>
        ) : (
          <div className="active-project-sidebar">
            <button className="active-project-back" type="button" onClick={onClearActiveProject}>
              <BackIcon size={14} />
              <span>Recent projects</span>
            </button>
            {project.path && (
              <div className="active-project-heading">
                <p title={displayPath(project.path)}>{displayPath(project.path)}</p>
              </div>
            )}
            {viewNav}
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
