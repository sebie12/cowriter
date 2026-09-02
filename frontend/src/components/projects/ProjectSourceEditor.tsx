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
  const selectedPathRef = useRef<string | null>(null);

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

  const save = async () => {
    const pathToSave = selectedPath;
    if (!pathToSave || content === savedContent || isSaving) {
      return;
    }
    setIsSaving(true);
    setError(null);
    try {
      await filesystemService.writeSourceFile(project, pathToSave, content);
      if (selectedPathRef.current === pathToSave) {
        setSavedContent(content);
      }
    } catch (saveError) {
      setError(errorMessage(saveError, "Could not save the LaTeX file."));
    } finally {
      setIsSaving(false);
    }
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
            onChange={(event) => setSelectedPath(event.target.value)}
          >
            {files.length === 0 && <option value="">No .tex files</option>}
            {files.map((file) => (
              <option key={file.relativePath} value={file.relativePath}>{file.relativePath}</option>
            ))}
          </select>
        </label>
        <div className="source-editor-actions">
          <span>{content !== savedContent ? "Unsaved changes" : selectedPath ? "Saved" : ""}</span>
          <button
            type="button"
            className="source-refresh-button"
            onClick={() => setReloadVersion((version) => version + 1)}
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
        <p className="source-editor-state">Loading source...</p>
      ) : selectedPath ? (
        <CodeMirror
          className="source-code-mirror"
          value={content}
          height="100%"
          theme="dark"
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
