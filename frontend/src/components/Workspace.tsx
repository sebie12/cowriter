import { Composer } from "./composer/Composer";
import { Conversation } from "./Conversation";
import type { Project } from "../types";

interface WorkspaceProps {
  project: Project | null;
  isSending: boolean;
  error: string | null;
  onSendMessage: (message: string) => void;
  onSelectPrompt: (prompt: string) => void;
}

const starterPrompts = [
  "Start an essay about the social effects of printing technology",
  "Research a topic: AI agents in knowledge work",
  "Analyze sources for a literature review",
];

function WorkspaceHeader({ project }: { project: Project | null }) {
  return (
    <header className="workspace-header">
      <div>
        <p className="eyebrow">Writing workspace</p>
        <h1>{project ? project.title : "New research session"}</h1>
      </div>
      <button className="tool-placeholder" type="button">Tools soon</button>
    </header>
  );
}

function EmptyState({ onSelectPrompt }: { onSelectPrompt: (prompt: string) => void }) {
  return (
    <section className="empty-state" aria-label="Start workspace">
      <p className="eyebrow">Draft, research, revise</p>
      <h2>What are you working on?</h2>
      <p>
        Start with a prompt, open a recent project, or create a new writing session. AI features are mocked for now.
      </p>
      <div className="starter-actions">
        {starterPrompts.map((prompt) => (
          <button key={prompt} type="button" onClick={() => onSelectPrompt(prompt)}>
            {prompt.split(":")[0]}
          </button>
        ))}
      </div>
    </section>
  );
}

export function Workspace({ project, isSending, error, onSendMessage, onSelectPrompt }: WorkspaceProps) {
  return (
    <main className="workspace">
      <WorkspaceHeader project={project} />
      {error && (
        <div className="error-banner" role="alert">
          Could not reach Flask. Start the backend and try again. <span>{error}</span>
        </div>
      )}
      <div className="workspace-body">
        {project ? (
          <Conversation messages={project.messages} isSending={isSending} />
        ) : (
          <EmptyState onSelectPrompt={onSelectPrompt} />
        )}
      </div>
      <Composer onSend={onSendMessage} disabled={isSending} />
    </main>
  );
}
