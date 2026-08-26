import { DataIcon } from "../ui/Icons";

export type SettingsSection = "model-providers";

interface SettingsSidebarProps {
  selectedSection: SettingsSection;
  onSelectSection: (section: SettingsSection) => void;
}

export function SettingsSidebar({ selectedSection, onSelectSection }: SettingsSidebarProps) {
  return (
    <nav className="settings-sidebar" aria-label="Settings sections">
      <h1 id="settings-title">Settings</h1>
      <button
        className={selectedSection === "model-providers" ? "active" : ""}
        type="button"
        aria-current={selectedSection === "model-providers" ? "page" : undefined}
        onClick={() => onSelectSection("model-providers")}
      >
        <DataIcon className="settings-nav-icon" />
        <span>Model Providers</span>
      </button>
    </nav>
  );
}
