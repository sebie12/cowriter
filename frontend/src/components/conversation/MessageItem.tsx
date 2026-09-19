import { useState } from "react";
import type { Message } from "../../types";
import { MarkdownContent } from "../MarkdownContent";
import { CheckIcon, CopyIcon } from "../ui/Icons";

interface MessageItemProps {
  message: Message;
}

function MessageActions({ message, quiet = false }: MessageItemProps & { quiet?: boolean }) {
  const [copied, setCopied] = useState(false);
  const [copyStatus, setCopyStatus] = useState<string | null>(null);
  if (!message.content) {
    return null;
  }

  const copy = async () => {
    if (!navigator.clipboard) {
      setCopyStatus("Clipboard access is unavailable");
      return;
    }
    try {
      await navigator.clipboard.writeText(message.content);
      setCopied(true);
      setCopyStatus("Message copied");
      window.setTimeout(() => {
        setCopied(false);
        setCopyStatus(null);
      }, 1200);
    } catch {
      setCopyStatus("Could not copy the message");
    }
  };

  return (
    <div className={`message-actions ${quiet ? "quiet" : ""}`}>
      <time dateTime={message.createdAt} title={new Date(message.createdAt).toLocaleString()}>
        {new Date(message.createdAt).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
      </time>
      <button type="button" onClick={() => void copy()} aria-label={copied ? "Copied" : "Copy message"}>
        {copied ? <CheckIcon /> : <CopyIcon />}
      </button>
      {copyStatus && <span className="sr-only" role="status">{copyStatus}</span>}
    </div>
  );
}

function TypingIndicator() {
  return (
    <div className="typing-indicator" role="status" aria-label="Cowriter is drafting a response">
      <span>Drafting</span>
      <i aria-hidden="true" />
      <i aria-hidden="true" />
      <i aria-hidden="true" />
    </div>
  );
}

export function MessageItem({ message }: MessageItemProps) {
  const status = message.status ?? "complete";
  const authorId = `message-${message.id}-author`;

  if (message.role === "user") {
    return (
      <article className="message-row user-message" data-message-status={status} aria-labelledby={authorId}>
        <h2 id={authorId} className="sr-only">You</h2>
        <div className="message-bubble">{message.content}</div>
        <MessageActions message={message} quiet />
      </article>
    );
  }

  return (
    <article className="message-row assistant-message" data-message-status={status} aria-labelledby={authorId}>
      <h2 id={authorId} className="sr-only">Cowriter</h2>
      {message.content ? <MarkdownContent content={message.content} /> : status === "streaming" ? <TypingIndicator /> : null}
      {status === "streaming" && message.content && <span className="streaming-caret" aria-hidden="true" />}
      {status === "stopped" && <span className="message-status" role="status">Response stopped</span>}
      {status === "error" && <span className="message-status error" role="status">Response interrupted by an error</span>}
      {status !== "streaming" && <MessageActions message={message} />}
    </article>
  );
}
