import { useEffect, useState } from "react";
import type { Message } from "../types";
import { MessageItem } from "./conversation/MessageItem";

interface ConversationProps {
  messages: Message[];
  isSending: boolean;
}

const DEFAULT_ZOOM = 100;
const MIN_ZOOM = 75;
const MAX_ZOOM = 200;
const ZOOM_STEP = 10;

export function Conversation({ messages, isSending }: ConversationProps) {
  const [zoom, setZoom] = useState(DEFAULT_ZOOM);

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
      {messages.map((message) => <MessageItem key={message.id} message={message} />)}
    </section>
  );
}
