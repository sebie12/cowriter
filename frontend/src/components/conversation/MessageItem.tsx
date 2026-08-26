import { useState } from "react";
import type { Message } from "../../types";
import { MarkdownContent } from "../MarkdownContent";
import { CheckIcon, CopyIcon } from "../ui/Icons";

interface MessageItemProps {
  message: Message;
}

function MessageActions({ message, quiet = false }: MessageItemProps & { quiet?: boolean }) {
  const [copied, setCopied] = useState(false);
  if (!message.content) {
    return null;
  }

  const copy = async () => {
    if (!navigator.clipboard) {
      return;
    }
    await navigator.clipboard.writeText(message.content);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1200);
  };

  return (
    <div className={`message-actions ${quiet ? "quiet" : ""}`}>
      <time dateTime={message.createdAt} title={new Date(message.createdAt).toLocaleString()}>
        {new Date(message.createdAt).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
      </time>
      <button type="button" onClick={() => void copy()} aria-label={copied ? "Copied" : "Copy message"}>
        {copied ? <CheckIcon /> : <CopyIcon />}
      </button>
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

  if (message.role === "user") {
    return (
      <article className="message-row user-message" data-message-status={status}>
        <div className="message-bubble">{message.content}</div>
        <MessageActions message={message} quiet />
      </article>
    );
  }

  return (
    <article className="message-row assistant-message" data-message-status={status}>
      {message.content ? <MarkdownContent content={message.content} /> : status === "streaming" ? <TypingIndicator /> : null}
      {status === "streaming" && message.content && <span className="streaming-caret" aria-hidden="true" />}
      {status === "stopped" && <span className="message-status">Response stopped</span>}
      {status === "error" && <span className="message-status error">Response interrupted by an error</span>}
      {status !== "streaming" && <MessageActions message={message} />}
    </article>
  );
}
