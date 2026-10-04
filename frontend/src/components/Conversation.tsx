import type { ConversationItem } from "../types";
import { MessageItem, TypingIndicator } from "./conversation/MessageItem";
import { ToolCallItem } from "./conversation/ToolCallItem";

interface ConversationProps {
  items: ConversationItem[];
  isSending: boolean;
}

export function Conversation({ items, isSending }: ConversationProps) {
  if (items.length === 0 && !isSending) {
    return (
      <div className="project-empty-state">
        <h2>Start this project</h2>
        <p>Ask a question, draft a paragraph, or paste notes into the composer below.</p>
      </div>
    );
  }

  return (
    <section
      className="conversation"
      aria-label="Conversation"
      aria-busy={isSending}
    >
      {items.map((item) => item.kind === "message"
        ? <MessageItem key={item.id} message={item} />
        : <ToolCallItem key={item.id} toolCall={item} />)}
      {isSending
        && !items.some((item) => item.kind === "message" && item.status === "streaming")
        && !items.some((item) => item.kind === "tool-call" && ["pending", "running"].includes(item.status))
        && (
          <div className="message-row assistant-message conversation-progress">
            <TypingIndicator label="Thinking" />
          </div>
        )}
    </section>
  );
}
