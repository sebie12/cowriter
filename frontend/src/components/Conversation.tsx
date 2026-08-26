import { useEffect, useState } from "react";
import cowriterPet from "../assets/icons/cowriter_pet.svg";
import { MarkdownContent } from "./MarkdownContent";
import type { Message } from "../types";

interface ConversationProps {
  messages: Message[];
  isSending: boolean;
}

const DEFAULT_ZOOM = 100;
const MIN_ZOOM = 75;
const MAX_ZOOM = 200;
const ZOOM_STEP = 10;

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
  const [zoom, setZoom] = useState(DEFAULT_ZOOM);
  const isAwaitingResponse = isSending && messages[messages.length - 1]?.role !== "assistant";

  useEffect(() => {
    const handleZoomShortcut = (event: KeyboardEvent) => {
      if ((!event.ctrlKey && !event.metaKey) || event.altKey) {
        return;
      }

      if (event.key === "+" || event.key === "=") {
        event.preventDefault();
        setZoom((currentZoom) => Math.min(currentZoom + ZOOM_STEP, MAX_ZOOM));
      } else if (event.key === "-") {
        event.preventDefault();
        setZoom((currentZoom) => Math.max(currentZoom - ZOOM_STEP, MIN_ZOOM));
      } else if (event.key === "0") {
        event.preventDefault();
        setZoom(DEFAULT_ZOOM);
      }
    };

    window.addEventListener("keydown", handleZoomShortcut);
    return () => window.removeEventListener("keydown", handleZoomShortcut);
  }, []);

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
      style={{ fontSize: `${zoom}%` }}
    >
      {messages.map((message) =>
        message.role === "user" ? (
          <UserMessage key={message.id} message={message} />
        ) : (
          <AssistantMessage key={message.id} message={message} />
        ),
      )}
      {isAwaitingResponse && <TypingIndicator />}
    </section>
  );
}
