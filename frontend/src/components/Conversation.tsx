import type { Message } from "../types";
import { MessageItem } from "./conversation/MessageItem";

interface ConversationProps {
  messages: Message[];
  isSending: boolean;
}

export function Conversation({ messages, isSending }: ConversationProps) {
  if (messages.length === 0 && !isSending) {
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
      {messages.map((message) => <MessageItem key={message.id} message={message} />)}
    </section>
  );
}
