import { useState } from "react";
import { openExternalUrl } from "../../services/externalLinks";
import type { Paper, Reference } from "../../types";
import { CheckIcon } from "../ui/Icons";

interface PaperDetailProps {
  paper: Paper;
  savedReference: Reference | undefined;
  isPending: boolean;
  onSave: (paper: Paper) => void;
  onRemove: (reference: Reference) => void;
}

function httpsUrl(url: string | null): string | null {
  if (!url) {
    return null;
  }
  try {
    return new URL(url).protocol === "https:" ? url : null;
  } catch {
    return null;
  }
}

export function formatAuthors(authors: string[], max = 3): string {
  if (authors.length === 0) {
    return "Unknown authors";
  }
  return authors.length > max ? `${authors.slice(0, max).join(", ")} et al.` : authors.join(", ");
}

export function PaperDetail({ paper, savedReference, isPending, onSave, onRemove }: PaperDetailProps) {
  const [linkError, setLinkError] = useState<string | null>(null);
  const links = [
    { label: "OpenAlex", url: httpsUrl(paper.url) },
    { label: "DOI", url: paper.doi ? `https://doi.org/${encodeURI(paper.doi)}` : null },
    { label: "PDF", url: httpsUrl(paper.pdfUrl) },
  ].filter((link): link is { label: string; url: string } => link.url !== null);

  const meta = [
    paper.year ? String(paper.year) : null,
    paper.venue,
    paper.citationCount !== null ? `${paper.citationCount.toLocaleString()} citations` : null,
  ].filter(Boolean);

  return (
    <article className="paper-detail" aria-label="Paper details">
      <div className="paper-detail-scroll">
        {meta.length > 0 && <p className="paper-detail-meta">{meta.join(" · ")}</p>}
        <h2>{paper.title}</h2>
        <p className="paper-detail-authors">{formatAuthors(paper.authors, 12)}</p>

        {paper.tldr && (
          <section className="paper-detail-section paper-tldr">
            <h3>TL;DR</h3>
            <p>{paper.tldr}</p>
          </section>
        )}
        <section className="paper-detail-section">
          <h3>Abstract</h3>
          <p>{paper.abstract ?? "No abstract available."}</p>
        </section>

        {links.length > 0 && (
          <div className="paper-detail-links">
            {links.map((link) => (
              <button
                type="button"
                key={link.label}
                onClick={() => {
                  setLinkError(null);
                  void openExternalUrl(link.url).catch((error) => {
                    setLinkError(error instanceof Error ? error.message : "Could not open the link.");
                  });
                }}
              >
                {link.label} ↗
              </button>
            ))}
          </div>
        )}
        {linkError && <p className="paper-detail-error" role="alert">{linkError}</p>}
      </div>

      <footer className="paper-detail-footer">
        {savedReference ? (
          <>
            <span className="paper-saved-label"><CheckIcon aria-hidden="true" /> Saved to references</span>
            <button
              type="button"
              className="paper-remove-button"
              disabled={isPending}
              onClick={() => onRemove(savedReference)}
            >
              Remove
            </button>
          </>
        ) : (
          <button
            type="button"
            className="paper-save-button"
            disabled={isPending}
            onClick={() => onSave(paper)}
          >
            {isPending ? "Saving…" : "Save to references"}
          </button>
        )}
      </footer>
    </article>
  );
}
