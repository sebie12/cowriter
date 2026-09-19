import { useEffect, useRef, useState } from "react";
import { StreamLanguage } from "@codemirror/language";
import { stex } from "@codemirror/legacy-modes/mode/stex";
import CodeMirror from "@uiw/react-codemirror";
import type { ProjectFilesystemService } from "../../services/projectFilesystem";
import type { Project, ProjectSourceFile } from "../../types";
import { RefreshIcon } from "../ui/Icons";

interface ProjectSourceEditorProps {
  project: Project;
  filesystemService: ProjectFilesystemService;
}

const latexLanguage = StreamLanguage.define(stex);

function errorMessage(error: unknown, fallback: string): string {
  if (typeof error === "string" && error.trim()) {
    return error;
  }
  return error instanceof Error ? error.message : fallback;
}

export function ProjectSourceEditor({ project, filesystemService }: ProjectSourceEditorProps) {
  const [files, setFiles] = useState<ProjectSourceFile[]>([]);
  const [selectedPath, setSelectedPath] = useState<string | null>(null);
  const [content, setContent] = useState("");
  const [savedContent, setSavedContent] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [reloadVersion, setReloadVersion] = useState(0);
  const [darkAppearance, setDarkAppearance] = useState(() => window.matchMedia("(prefers-color-scheme: dark)").matches);
  const selectedPathRef = useRef<string | null>(null);
  const contentRef = useRef(content);
  contentRef.current = content;

  useEffect(() => {
    const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");
    const updateAppearance = () => setDarkAppearance(mediaQuery.matches);
    mediaQuery.addEventListener("change", updateAppearance);
    return () => mediaQuery.removeEventListener("change", updateAppearance);
  }, []);

  useEffect(() => {
    let cancelled = false;
    setFiles([]);
    setSelectedPath(null);
    selectedPathRef.current = null;
    setContent("");
    setSavedContent("");
    setError(null);
    setIsLoading(true);

    if (!project.path || !filesystemService.directorySelectionAvailable) {
      setIsLoading(false);
      return;
    }

    void filesystemService.listLatexFiles(project)
      .then((nextFiles) => {
        if (cancelled) {
          return;
        }
        setFiles(nextFiles);
        setSelectedPath(nextFiles[0]?.relativePath ?? null);
        if (nextFiles.length === 0) {
          setIsLoading(false);
        }
      })
      .catch((loadError) => {
        if (!cancelled) {
          setError(errorMessage(loadError, "Could not load LaTeX files."));
          setIsLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [filesystemService, project.id, project.path, reloadVersion]);

  useEffect(() => {
    selectedPathRef.current = selectedPath;
    if (!selectedPath) {
      return;
    }

    let cancelled = false;
    setIsLoading(true);
    setError(null);
    void filesystemService.readSourceFile(project, selectedPath)
      .then((nextContent) => {
        if (!cancelled) {
          setContent(nextContent);
          setSavedContent(nextContent);
        }
      })
      .catch((loadError) => {
        if (!cancelled) {
          setError(errorMessage(loadError, "Could not read the LaTeX file."));
        }
      })
      .finally(() => {
        if (!cancelled) {
          setIsLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [filesystemService, project.id, project.path, selectedPath]);

  const save = async (): Promise<boolean> => {
    const pathToSave = selectedPath;
    if (!pathToSave || isSaving) {
      return false;
    }
    if (content === savedContent) {
      return true;
    }
    const contentToSave = content;
    setIsSaving(true);
    setError(null);
    try {
      await filesystemService.writeSourceFile(project, pathToSave, contentToSave);
      if (selectedPathRef.current === pathToSave) {
        setSavedContent(contentToSave);
      }
      return contentRef.current === contentToSave;
    } catch (saveError) {
      setError(errorMessage(saveError, "Could not save the LaTeX file."));
      return false;
    } finally {
      setIsSaving(false);
    }
  };

  const selectFile = async (nextPath: string) => {
    if (nextPath === selectedPath) {
      return;
    }
    if (content !== savedContent && !(await save())) {
      return;
    }
    setSelectedPath(nextPath);
  };

  const refreshFiles = async () => {
    if (content !== savedContent && !(await save())) {
      return;
    }
    setReloadVersion((version) => version + 1);
  };

  if (!filesystemService.directorySelectionAvailable) {
    return <p className="source-editor-state">Source files are only available in the desktop app.</p>;
  }
  if (!project.path) {
    return <p className="source-editor-state">No project directory configured.</p>;
  }

  return (
    <section
      className="source-editor"
      aria-label="Project LaTeX source editor"
      onKeyDownCapture={(event) => {
        if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "s") {
          event.preventDefault();
          void save();
        }
      }}
    >
      <div className="source-editor-bar">
        <label>
          <span>File</span>
          <select
            value={selectedPath ?? ""}
            disabled={files.length === 0 || isLoading || isSaving}
            onChange={(event) => void selectFile(event.target.value)}
          >
            {files.length === 0 && <option value="">No .tex files</option>}
            {files.map((file) => (
              <option key={file.relativePath} value={file.relativePath}>{file.relativePath}</option>
            ))}
          </select>
        </label>
        <div className="source-editor-actions">
          <span role="status" aria-live="polite">{isSaving ? "Saving..." : content !== savedContent ? "Unsaved changes" : selectedPath ? "Saved" : ""}</span>
          <button
            type="button"
            className="source-refresh-button"
            disabled={isLoading || isSaving}
            onClick={() => void refreshFiles()}
            aria-label="Refresh source files"
          >
            <RefreshIcon size={14} />
          </button>
          <button
            type="button"
            className="source-save-button"
            disabled={!selectedPath || content === savedContent || isSaving}
            onClick={() => void save()}
          >
            {isSaving ? "Saving..." : "Save"}
          </button>
        </div>
      </div>
      {error && <div className="source-editor-error" role="alert">{error}</div>}
      {isLoading ? (
        <p className="source-editor-state" role="status">Loading source...</p>
      ) : selectedPath ? (
        <CodeMirror
          className="source-code-mirror"
          value={content}
          editable={!isSaving}
          height="100%"
          theme={darkAppearance ? "dark" : "light"}
          extensions={[latexLanguage]}
          basicSetup={{
            bracketMatching: true,
            closeBrackets: true,
            foldGutter: true,
            highlightActiveLine: true,
            highlightActiveLineGutter: true,
            lineNumbers: true,
          }}
          onChange={setContent}
        />
      ) : (
        <p className="source-editor-state">No LaTeX source files found in this project.</p>
      )}
    </section>
  );
}
