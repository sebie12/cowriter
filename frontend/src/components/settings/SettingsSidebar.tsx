export type SettingsSection = "model-providers";

interface SettingsSidebarProps {
  selectedSection: SettingsSection;
  onSelectSection: (section: SettingsSection) => void;
}

export function SettingsSidebar({ selectedSection, onSelectSection }: SettingsSidebarProps) {
  return (
    <nav className="settings-sidebar" aria-label="Settings sections">
      <button
        className={selectedSection === "model-providers" ? "active" : ""}
        type="button"
        aria-current={selectedSection === "model-providers" ? "page" : undefined}
        onClick={() => onSelectSection("model-providers")}
      >
        <span className="settings-nav-icon" aria-hidden="true">M</span>
        <span>Model Providers</span>
      </button>
    </nav>
  );
}
