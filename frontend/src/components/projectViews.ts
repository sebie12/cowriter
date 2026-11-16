export type ProjectView = "work" | "research" | "chat";

export const PROJECT_VIEWS: Array<{ id: ProjectView; label: string }> = [
  { id: "work", label: "Work" },
  { id: "research", label: "Research" },
  { id: "chat", label: "Chat" },
];
