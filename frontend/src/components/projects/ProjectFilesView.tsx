import { useEffect, useState } from "react";
import type { ProjectFilesystemService } from "../../services/projectFilesystem";
import type { Project, ProjectFileEntry } from "../../types";
import { FileIcon, FolderIcon, RefreshIcon } from "../ui/Icons";

type FilesStatus = "loading" | "success" | "error";

interface ProjectFilesViewProps {
  project: Project;
  filesystemService: ProjectFilesystemService;
}

export function ProjectFilesView({ project, filesystemService }: ProjectFilesViewProps) {
  const [status, setStatus] = useState<FilesStatus>("loading");
  const [entries, setEntries] = useState<ProjectFileEntry[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [reloadVersion, setReloadVersion] = useState(0);

  useEffect(() => {
    if (!project.path || !filesystemService.directorySelectionAvailable) {
      setStatus("success");
      setEntries([]);
      setError(null);
      return;
    }

    let cancelled = false;
    setStatus("loading");
    setEntries([]);
    setError(null);
    void filesystemService.listFiles(project)
      .then((nextEntries) => {
        if (!cancelled) {
          setEntries(nextEntries);
          setStatus("success");
        }
      })
      .catch((loadError) => {
        if (!cancelled) {
          setError(loadError instanceof Error ? loadError.message : "Could not read the project directory.");
          setStatus("error");
        }
      });
    return () => {
      cancelled = true;
    };
  }, [filesystemService, project.id, project.path, reloadVersion]);

  if (!filesystemService.directorySelectionAvailable) {
    return <p className="project-files-state">Project files are only available in the desktop app.</p>;
  }
  if (!project.path) {
    return <p className="project-files-state">No project directory configured.</p>;
  }
  if (status === "loading") {
    return <p className="project-files-state">Loading files...</p>;
  }
  if (status === "error") {
    return (
      <div className="project-files-error" role="alert">
        <p>{error}</p>
        <button type="button" onClick={() => setReloadVersion((version) => version + 1)}>
          <RefreshIcon size={13} /> Retry
        </button>
      </div>
    );
  }
  if (entries.length === 0) {
    return <p className="project-files-state">No files in this project yet.</p>;
  }

  return (
    <ul className="project-files-list">
      {entries.map((entry) => (
        <li key={`${entry.kind}:${entry.name}`} title={entry.name}>
          {entry.kind === "directory" ? <FolderIcon /> : <FileIcon />}
          <span>{entry.name}</span>
        </li>
      ))}
    </ul>
  );
}
