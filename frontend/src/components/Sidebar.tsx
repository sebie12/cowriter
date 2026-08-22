import cowriterPet from "../assets/icons/cowriter_pet.svg";
import type { Project } from "../types";

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

interface ProjectListProps {
  collapsed: boolean;
  projects: Project[];
  selectedProjectId: string | null;
  onSelectProject: (projectId: string) => void;
}

function NewProjectButton({ collapsed, onNewProject }: { collapsed: boolean; onNewProject: () => void }) {
  return (
    <button className="new-project-button" type="button" onClick={onNewProject} title="New project">
      <span aria-hidden="true">+</span>
      {!collapsed && <span>New project</span>}
    </button>
  );
}

function ProjectList({ collapsed, projects, selectedProjectId, onSelectProject }: ProjectListProps) {
  return (
    <nav className="project-list" aria-label="Recent projects">
      {!collapsed && <div className="sidebar-section-label">Recent work</div>}
      {projects.map((project) => (
        <button
          className={`project-item ${project.id === selectedProjectId ? "active" : ""}`}
          key={project.id}
          type="button"
          title={project.title}
          onClick={() => onSelectProject(project.id)}
        >
          <span className="project-dot" aria-hidden="true" />
          {!collapsed && <span>{project.title}</span>}
        </button>
      ))}
    </nav>
  );
}

interface SidebarFooterProps {
  collapsed: boolean;
  settingsActive: boolean;
  onOpenSettings: () => void;
}

function SidebarFooter({ collapsed, settingsActive, onOpenSettings }: SidebarFooterProps) {
  return (
    <footer className="sidebar-footer">
      <button
        className={`footer-button ${settingsActive ? "active" : ""}`}
        type="button"
        title="Settings"
        aria-current={settingsActive ? "page" : undefined}
        onClick={onOpenSettings}
      >
        <span aria-hidden="true">S</span>
        {!collapsed && <span>Settings</span>}
      </button>
      <button className="footer-button" type="button" title="Account/Profile">
        <span aria-hidden="true">A</span>
        {!collapsed && <span>Account/Profile</span>}
      </button>
    </footer>
  );
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
  return (
    <aside className={`sidebar ${collapsed ? "collapsed" : ""}`}>
      <div className="sidebar-header">
        <div className="brand" title="Cowriter">
          <span className="brand-mark" aria-hidden="true">
            <img src={cowriterPet} alt="" />
          </span>
          {!collapsed && <span className="brand-name">Cowriter</span>}
        </div>
        <button
          className="icon-button"
          type="button"
          onClick={onToggleCollapsed}
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          {collapsed ? ">" : "<"}
        </button>
      </div>
      <NewProjectButton collapsed={collapsed} onNewProject={onNewProject} />
      <ProjectList
        collapsed={collapsed}
        projects={projects}
        selectedProjectId={selectedProjectId}
        onSelectProject={onSelectProject}
      />
      <SidebarFooter collapsed={collapsed} settingsActive={settingsActive} onOpenSettings={onOpenSettings} />
    </aside>
  );
}
