import { FormEvent, useEffect, useRef, useState } from "react";
import type { ProjectFilesystemService } from "../../services/projectFilesystem";
import type { CreateProjectInput } from "../../types";
import { useDialogFocus } from "../../hooks/useDialogFocus";
import { CloseIcon } from "../ui/Icons";
import {
  DEFAULT_PROJECT_CONTEXT,
  ProjectContextFields,
  type ProjectContextValue,
} from "./ProjectContextFields";

type SubmissionStatus = "idle" | "submitting" | "success" | "error";

interface ProjectModalProps {
  filesystemService: ProjectFilesystemService;
  initialName?: string;
  onCreateProject: (input: CreateProjectInput) => Promise<void>;
  onClose: () => void;
}

export function ProjectModal({
  filesystemService,
  initialName = "",
  onCreateProject,
  onClose,
}: ProjectModalProps) {
  const [name, setName] = useState(initialName);
  const [context, setContext] = useState<ProjectContextValue>(DEFAULT_PROJECT_CONTEXT);
  const [directoryPath, setDirectoryPath] = useState<string | null>(null);
  const [status, setStatus] = useState<SubmissionStatus>("idle");
  const [error, setError] = useState<string | null>(null);
  const [isSelectingDirectory, setIsSelectingDirectory] = useState(false);
  const nameInputRef = useRef<HTMLInputElement | null>(null);
  const dialogRef = useRef<HTMLElement | null>(null);
  const submissionInProgressRef = useRef(false);
  const submitting = status === "submitting";

  const closeModal = () => {
    if (!submitting) {
      onClose();
    }
  };

  useDialogFocus(dialogRef, nameInputRef);

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        closeModal();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [submitting]);

  const selectDirectory = async () => {
    if (isSelectingDirectory || submitting) {
      return;
    }
    setIsSelectingDirectory(true);
    setError(null);
    try {
      const path = await filesystemService.selectDirectory();
      if (path) {
        setDirectoryPath(path);
      }
    } catch (selectionError) {
      setError(selectionError instanceof Error ? selectionError.message : "Could not select the project directory.");
    } finally {
      setIsSelectingDirectory(false);
    }
  };

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (submissionInProgressRef.current) {
      return;
    }
    const normalizedName = name.trim();
    if (!normalizedName) {
      setStatus("error");
      setError("Enter a project name to continue.");
      nameInputRef.current?.focus();
      return;
    }

    submissionInProgressRef.current = true;
    setStatus("submitting");
    setError(null);
    try {
      await onCreateProject({
        name: normalizedName,
        writingContext: context,
        path: directoryPath,
      });
      setStatus("success");
      onClose();
    } catch (creationError) {
      setStatus("error");
      setError(creationError instanceof Error ? creationError.message : "Could not create the project.");
    } finally {
      submissionInProgressRef.current = false;
    }
  };

  return (
    <div className="settings-overlay">
      <div className="settings-mask" aria-hidden="true" onMouseDown={closeModal} />
      <section ref={dialogRef} className="project-modal" role="dialog" aria-modal="true" aria-labelledby="project-modal-title" tabIndex={-1}>
        <header className="project-modal-header">
          <div>
            <p className="eyebrow">New project</p>
            <h1 id="project-modal-title">Set up your writing space</h1>
          </div>
          <button className="settings-close-button" type="button" onClick={closeModal} disabled={submitting} aria-label="Close project creation">
            <CloseIcon />
          </button>
        </header>

        <form className="project-modal-form" onSubmit={(event) => void submit(event)}>
          <label className="project-name-field">
            <span>Project name</span>
            <input
              ref={nameInputRef}
              value={name}
              maxLength={100}
              readOnly={submitting}
              placeholder="Research Essay"
              aria-invalid={status === "error" && !name.trim() ? true : undefined}
              aria-errormessage={status === "error" && !name.trim() ? "project-modal-error" : undefined}
              onChange={(event) => {
                setName(event.target.value);
                if (status === "error") {
                  setStatus("idle");
                  setError(null);
                }
              }}
            />
          </label>

          <ProjectContextFields value={context} disabled={submitting} onChange={setContext} />

          <section className="project-directory-field" aria-labelledby="project-directory-title">
            <div>
              <h2 id="project-directory-title">Project directory</h2>
              <p>Files in this folder will appear in the project sidebar.</p>
            </div>
            {filesystemService.directorySelectionAvailable ? (
              <>
                <button type="button" disabled={submitting || isSelectingDirectory} onClick={() => void selectDirectory()}>
                  {isSelectingDirectory ? "Selecting..." : directoryPath ? "Change folder" : "Select folder"}
                </button>
                {directoryPath && <p className="project-directory-path" title={directoryPath}>{directoryPath}</p>}
              </>
            ) : (
              <p className="project-directory-unavailable">Directory selection is only available in the desktop app.</p>
            )}
          </section>

          {error && <p id="project-modal-error" className="project-modal-error" role="alert">{error}</p>}

          <footer className="project-modal-actions">
            <button className="project-modal-cancel" type="button" disabled={submitting} onClick={closeModal}>Cancel</button>
            <button
              className="project-modal-continue"
              type="submit"
              disabled={!name.trim()}
              aria-disabled={submitting || !name.trim()}
            >
              {submitting ? "Creating..." : status === "success" ? "Created" : "Continue"}
            </button>
          </footer>
        </form>
      </section>
    </div>
  );
}
