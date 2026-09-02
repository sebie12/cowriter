import { invoke } from "@tauri-apps/api/core";
import { open } from "@tauri-apps/plugin-dialog";
import type { Project, ProjectFileEntry, ProjectSourceFile } from "../types";

export interface ProjectFilesystemService {
  readonly directorySelectionAvailable: boolean;
  selectDirectory(): Promise<string | null>;
  listFiles(project: Pick<Project, "path">): Promise<ProjectFileEntry[]>;
  listLatexFiles(project: Pick<Project, "path">): Promise<ProjectSourceFile[]>;
  readSourceFile(project: Pick<Project, "path">, relativePath: string): Promise<string>;
  writeSourceFile(project: Pick<Project, "path">, relativePath: string, content: string): Promise<void>;
}

function isTauriRuntime(): boolean {
  return "__TAURI_INTERNALS__" in window;
}

function projectPath(project: Pick<Project, "path">): string {
  if (!isTauriRuntime()) {
    throw new Error("Project files are only available in the desktop app.");
  }
  if (!project.path) {
    throw new Error("No project directory configured.");
  }
  return project.path;
}

async function invokeProjectCommand<T>(command: string, args: Record<string, unknown>): Promise<T> {
  try {
    return await invoke<T>(command, args);
  } catch (error) {
    throw error instanceof Error ? error : new Error(typeof error === "string" ? error : "Project file operation failed.");
  }
}

export const projectFilesystemService: ProjectFilesystemService = {
  get directorySelectionAvailable() {
    return isTauriRuntime();
  },

  async selectDirectory() {
    if (!isTauriRuntime()) {
      throw new Error("Directory selection is only available in the desktop app.");
    }
    const selection = await open({
      directory: true,
      multiple: false,
      recursive: false,
      title: "Choose a folder for this project",
    });
    return Array.isArray(selection) ? selection[0] ?? null : selection;
  },

  async listFiles(project) {
    if (!project.path) {
      return [];
    }
    return invokeProjectCommand<ProjectFileEntry[]>("list_project_files", { path: projectPath(project) });
  },

  async listLatexFiles(project) {
    if (!project.path) {
      return [];
    }
    return invokeProjectCommand<ProjectSourceFile[]>("list_latex_files", { path: projectPath(project) });
  },

  async readSourceFile(project, relativePath) {
    return invokeProjectCommand<string>("read_project_source", { path: projectPath(project), relativePath });
  },

  async writeSourceFile(project, relativePath, content) {
    await invokeProjectCommand<void>("write_project_source", { path: projectPath(project), relativePath, content });
  },
};
