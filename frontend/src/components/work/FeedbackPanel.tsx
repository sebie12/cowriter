import { useEffect, useRef } from "react";
import type { ProofreadIssue, ProofreadIssueType, Reference } from "../../types";

export const ISSUE_LABELS: Record<ProofreadIssueType, { label: string; plural: string; mark: string }> = {
  spelling: { label: "Spelling", plural: "Spelling", mark: "Aa" },
  grammar: { label: "Grammar", plural: "Grammar", mark: "G" },
  claim: { label: "Claim", plural: "Claims", mark: "!" },
  style: { label: "Style", plural: "Style", mark: "S" },
};
const ISSUE_ORDER: ProofreadIssueType[] = ["spelling", "grammar", "claim", "style"];

export type ReviewStatus = "idle" | "reviewing" | "reviewed" | "error";

interface FeedbackPanelProps {
  issues: ProofreadIssue[];
  status: ReviewStatus;
  error: string | null;
  activeId: string | null;
  filter: ProofreadIssueType | null;
  references: Reference[];
  hasReferences: boolean;
  essay: { file: string; truncated: boolean } | null;
  hasProjectFolder: boolean;
  onFilterChange: (filter: ProofreadIssueType | null) => void;
  onHover: (id: string | null) => void;
  onSelect: (id: string) => void;
  onApply: (issue: ProofreadIssue) => void;
  onDismiss: (issue: ProofreadIssue) => void;
}

function truncate(text: string, length: number) {
  const singleLine = text.replace(/\s+/g, " ").trim();
  return singleLine.length > length ? `${singleLine.slice(0, length - 1)}…` : singleLine;
}

export function FeedbackPanel({
  issues,
  status,
  error,
  activeId,
  filter,
  references,
  hasReferences,
  essay,
  hasProjectFolder,
  onFilterChange,
  onHover,
  onSelect,
  onApply,
  onDismiss,
}: FeedbackPanelProps) {
  const cardRefs = useRef(new Map<string, HTMLElement>());
  const counts = Object.fromEntries(
    ISSUE_ORDER.map((type) => [type, issues.filter((issue) => issue.type === type).length]),
  ) as Record<ProofreadIssueType, number>;
  const visibleIssues = filter ? issues.filter((issue) => issue.type === filter) : issues;
  const referenceById = new Map(references.map((reference) => [reference.id, reference]));

  useEffect(() => {
    if (activeId) {
      cardRefs.current.get(activeId)?.scrollIntoView({ block: "nearest" });
    }
  }, [activeId]);

  return (
    <aside className="feedback-panel" aria-label="Review feedback">
      <header className="feedback-header">
        <h2>Feedback</h2>
        {status === "reviewed" && <span className="feedback-total">{issues.length} open</span>}
      </header>

      <div className="feedback-filters" role="group" aria-label="Filter feedback by type">
        <button
          type="button"
          className={filter === null ? "active" : ""}
          aria-pressed={filter === null}
          onClick={() => onFilterChange(null)}
        >
          All <span>{issues.length}</span>
        </button>
        {ISSUE_ORDER.map((type) => (
          <button
            type="button"
            key={type}
            className={`issue-chip issue-chip--${type}${filter === type ? " active" : ""}`}
            aria-pressed={filter === type}
            onClick={() => onFilterChange(filter === type ? null : type)}
          >
            <span className="issue-swatch" aria-hidden="true" />
            {ISSUE_LABELS[type].plural} <span>{counts[type]}</span>
          </button>
        ))}
      </div>

      {status === "reviewed" && essay && (
        <p className="feedback-context">
          Compared with <code>{essay.file}</code>
          {essay.truncated && " (only the first part fit; the rest was not checked)"}
        </p>
      )}
      {status === "reviewed" && !essay && hasProjectFolder && (
        <p className="feedback-context">No LaTeX essay found in the project folder, so the draft was not compared with one.</p>
      )}
      {!hasReferences && (
        <p className="feedback-note">
          No references saved. Claims are only checked against general knowledge. Save papers in Research to check claims against them.
        </p>
      )}

      <div className="feedback-list" aria-live="polite">
        {status === "idle" && (
          <div className="feedback-empty">
            <p>Select <strong>Review draft</strong> to proofread your writing.</p>
            <ul className="feedback-legend">
              {ISSUE_ORDER.map((type) => (
                <li key={type}>
                  <span className={`issue-sample issue--${type}`}>{ISSUE_LABELS[type].label.toLowerCase()}</span>
                  {type === "spelling" && "Misspelled words"}
                  {type === "grammar" && "Grammatical errors"}
                  {type === "claim" && "False or unsupported claims, or ones that contradict your essay"}
                  {type === "style" && "Unclear or off-tone wording"}
                </li>
              ))}
            </ul>
          </div>
        )}
        {status === "reviewing" && (
          <div className="feedback-empty">
            <span className="review-spinner" aria-hidden="true" />
            <p>Reviewing your draft…</p>
          </div>
        )}
        {status === "error" && (
          <div className="feedback-error" role="alert">{error}</div>
        )}
        {status === "reviewed" && issues.length === 0 && (
          <div className="feedback-empty">
            <p>No open issues. Edit and review again any time.</p>
          </div>
        )}
        {status === "reviewed" && issues.length > 0 && visibleIssues.length === 0 && (
          <div className="feedback-empty"><p>No issues of this type.</p></div>
        )}
        {visibleIssues.map((issue) => {
          const citedReferences = issue.referenceIds
            .map((id) => referenceById.get(id))
            .filter((reference): reference is Reference => reference !== undefined);
          return (
            <article
              key={issue.id}
              ref={(element) => {
                if (element) {
                  cardRefs.current.set(issue.id, element);
                } else {
                  cardRefs.current.delete(issue.id);
                }
              }}
              className={`feedback-card feedback-card--${issue.type}${activeId === issue.id ? " active" : ""}`}
              tabIndex={0}
              aria-label={`${ISSUE_LABELS[issue.type].label}: ${truncate(issue.quote, 60)}`}
              onMouseEnter={() => onHover(issue.id)}
              onMouseLeave={() => onHover(null)}
              onFocus={() => onHover(issue.id)}
              onClick={(event) => {
                if ((event.target as HTMLElement).closest("button")) {
                  return;
                }
                onSelect(issue.id);
              }}
              onKeyDown={(event) => {
                if (event.target === event.currentTarget && (event.key === "Enter" || event.key === " ")) {
                  event.preventDefault();
                  onSelect(issue.id);
                }
              }}
            >
              <div className="feedback-card-head">
                <span className={`issue-badge issue-badge--${issue.type}`}>
                  <span aria-hidden="true">{ISSUE_LABELS[issue.type].mark}</span>
                  {ISSUE_LABELS[issue.type].label}
                </span>
              </div>
              <blockquote className="feedback-quote">“{truncate(issue.quote, 160)}”</blockquote>
              {issue.explanation && <p className="feedback-explanation">{issue.explanation}</p>}
              {issue.suggestion !== null && (
                <p className="feedback-suggestion">
                  <span>Suggestion</span>
                  {issue.suggestion ? issue.suggestion : <em>Remove this text</em>}
                </p>
              )}
              {citedReferences.length > 0 && (
                <ul className="feedback-references" aria-label="Related references">
                  {citedReferences.map((reference) => (
                    <li key={reference.id}>
                      {truncate(reference.title, 80)}
                      {reference.year ? ` (${reference.year})` : ""}
                    </li>
                  ))}
                </ul>
              )}
              <div className="feedback-actions">
                {issue.suggestion !== null && (
                  <button type="button" className="primary" onClick={() => onApply(issue)}>Apply</button>
                )}
                <button type="button" onClick={() => onDismiss(issue)}>Dismiss</button>
              </div>
            </article>
          );
        })}
      </div>
    </aside>
  );
}
