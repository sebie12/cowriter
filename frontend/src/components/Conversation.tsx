import { useEffect, useRef } from "react";
import cowriterPet from "../assets/icons/cowriter_pet.svg";
import { MarkdownContent } from "./MarkdownContent";
import type { Message } from "../types";

interface ConversationProps {
  messages: Message[];
  isSending: boolean;
}

function AssistantAvatar() {
  return (
    <div className="assistant-avatar" aria-hidden="true">
      <img src={cowriterPet} alt="" />
    </div>
  );
}

function UserMessage({ message }: { message: Message }) {
  return (
    <article className="message-row user-message">
      <div className="message-bubble">{message.content}</div>
    </article>
  );
}

function AssistantMessage({ message }: { message: Message }) {
  return (
    <article className="message-row assistant-message">
      <AssistantAvatar />
      <div className="assistant-content">
        <MarkdownContent content={message.content} />
      </div>
    </article>
  );
}

function TypingIndicator() {
  return (
    <article className="message-row assistant-message">
      <AssistantAvatar />
      <div className="typing-indicator" role="status">
        <span className="typing-label">Thinking</span>
        <span className="typing-dot" aria-hidden="true" />
        <span className="typing-dot" aria-hidden="true" />
        <span className="typing-dot" aria-hidden="true" />
      </div>
    </article>
  );
}

export function Conversation({ messages, isSending }: ConversationProps) {
  const endRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, isSending]);

  if (messages.length === 0 && !isSending) {
    return (
      <div className="project-empty-state">
        <h2>Start this project</h2>
        <p>Ask a question, draft a paragraph, or paste notes into the composer below.</p>
      </div>
    );
  }

  return (
    <section className="conversation" aria-label="Conversation" aria-busy={isSending}>
      {messages.map((message) =>
        message.role === "user" ? (
          <UserMessage key={message.id} message={message} />
        ) : (
          <AssistantMessage key={message.id} message={message} />
        ),
      )}
      {isSending && <TypingIndicator />}
      <div ref={endRef} />
    </section>
  );
}
