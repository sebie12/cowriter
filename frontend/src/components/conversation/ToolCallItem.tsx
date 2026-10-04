import { useId, useState } from "react";
import type { ToolCall, ToolCallStatus } from "../../types";
import { CheckIcon, ChevronDownIcon, ChevronRightIcon, CloseIcon, ToolIcon } from "../ui/Icons";

interface ToolCallItemProps {
  toolCall: ToolCall;
}

const STATUS_LABELS: Record<ToolCallStatus, string> = {
  pending: "Pending",
  running: "Running",
  completed: "Completed",
  failed: "Failed",
};

function StructuredValue({ value, unavailable }: { value: unknown; unavailable: string }) {
  if (value === null || value === undefined) {
    return <p className="tool-call-unavailable">{unavailable}</p>;
  }

  let content: string;
  if (typeof value === "string") {
    try {
      const parsed = JSON.parse(value) as unknown;
      content = typeof parsed === "object" && parsed !== null
        ? JSON.stringify(parsed, null, 2)
        : value;
    } catch {
      content = value;
    }
  } else {
    try {
      content = JSON.stringify(value, null, 2);
    } catch {
      content = String(value);
    }
  }

  return <pre><code>{content}</code></pre>;
}

function StatusMark({ status }: { status: ToolCallStatus }) {
  if (status === "completed") {
    return <CheckIcon size={14} />;
  }
  if (status === "failed") {
    return <CloseIcon size={14} />;
  }
  return <span className="tool-call-status-dot" aria-hidden="true" />;
}

function formatTimestamp(timestamp: string | null): string {
  if (!timestamp) {
    return "In progress";
  }
  const date = new Date(timestamp);
  return Number.isNaN(date.getTime()) ? "Unavailable" : date.toLocaleString();
}

function formatDuration(start: string, end: string | null): string {
  if (!end) {
    return "In progress";
  }
  const milliseconds = new Date(end).getTime() - new Date(start).getTime();
  if (!Number.isFinite(milliseconds) || milliseconds < 0) {
    return "Unavailable";
  }
  if (milliseconds < 1000) {
    return `${milliseconds} ms`;
  }
  if (milliseconds < 60_000) {
    return `${(milliseconds / 1000).toFixed(milliseconds < 10_000 ? 1 : 0)} s`;
  }
  const minutes = Math.floor(milliseconds / 60_000);
  const seconds = Math.round((milliseconds % 60_000) / 1000);
  return `${minutes} min ${seconds} s`;
}

export function ToolCallItem({ toolCall }: ToolCallItemProps) {
  const [expanded, setExpanded] = useState(false);
  const generatedId = useId().replace(/:/g, "");
  const detailsId = `tool-call-${generatedId}-details`;
  const nameId = `tool-call-${generatedId}-name`;

  return (
    <article
      className="tool-call-item"
      data-tool-status={toolCall.status}
      aria-labelledby={nameId}
    >
      <button
        className="tool-call-summary"
        type="button"
        aria-expanded={expanded}
        aria-controls={detailsId}
        onClick={() => setExpanded((current) => !current)}
      >
        <span className="tool-call-icon" aria-hidden="true"><ToolIcon /></span>
        <code id={nameId}>{toolCall.toolName}</code>
        <span className="tool-call-status" role="status">
          <StatusMark status={toolCall.status} />
          {STATUS_LABELS[toolCall.status]}
        </span>
        <span className="tool-call-disclosure" aria-hidden="true">
          {expanded ? <ChevronDownIcon /> : <ChevronRightIcon />}
        </span>
      </button>
      <div id={detailsId} className="tool-call-details" hidden={!expanded}>
        <dl className="tool-call-metadata">
          <div><dt>Tool</dt><dd><code>{toolCall.toolName}</code></dd></div>
          <div><dt>Status</dt><dd>{STATUS_LABELS[toolCall.status]}</dd></div>
          <div>
            <dt>Called</dt>
            <dd><time dateTime={toolCall.calledAt}>{formatTimestamp(toolCall.calledAt)}</time></dd>
          </div>
          <div>
            <dt>Finished</dt>
            <dd>{toolCall.finishedAt
              ? <time dateTime={toolCall.finishedAt}>{formatTimestamp(toolCall.finishedAt)}</time>
              : "In progress"}</dd>
          </div>
          <div><dt>Duration</dt><dd>{formatDuration(toolCall.calledAt, toolCall.finishedAt)}</dd></div>
        </dl>
        <section className="tool-call-data">
          <h3>Input</h3>
          <StructuredValue value={toolCall.input} unavailable="No input parameters." />
        </section>
        <section className="tool-call-data">
          <h3>Output</h3>
          <StructuredValue value={toolCall.output} unavailable="No output available yet." />
        </section>
        {toolCall.error && (
          <section className="tool-call-error" aria-label="Tool error">
            <h3>Error</h3>
            <pre><code>{toolCall.error}</code></pre>
          </section>
        )}
      </div>
    </article>
  );
}
