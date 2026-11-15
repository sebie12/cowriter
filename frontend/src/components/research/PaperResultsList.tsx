import { useEffect, useRef, type KeyboardEvent } from "react";
import type { Paper } from "../../types";
import { formatAuthors } from "./PaperDetail";

interface PaperResultsListProps {
  papers: Paper[];
  activeIndex: number;
  savedPaperIds: Set<string>;
  hasMore: boolean;
  isLoadingMore: boolean;
  onActiveChange: (index: number) => void;
  onLoadMore: () => void;
}

function scrollBehavior(): ScrollBehavior {
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth";
}

/**
 * A scroll-snapped list: whichever card crosses the vertical centre of the list
 * becomes active (larger, with details shown alongside).
 */
export function PaperResultsList({
  papers,
  activeIndex,
  savedPaperIds,
  hasMore,
  isLoadingMore,
  onActiveChange,
  onLoadMore,
}: PaperResultsListProps) {
  const listRef = useRef<HTMLDivElement | null>(null);
  const cardRefs = useRef<Array<HTMLDivElement | null>>([]);
  const onActiveChangeRef = useRef(onActiveChange);
  onActiveChangeRef.current = onActiveChange;

  useEffect(() => {
    const root = listRef.current;
    if (!root) {
      return;
    }
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            const index = Number((entry.target as HTMLElement).dataset.index);
            if (Number.isInteger(index)) {
              onActiveChangeRef.current(index);
            }
          }
        }
      },
      // A zero-height band across the middle of the list.
      { root, rootMargin: "-50% 0px -50% 0px", threshold: 0 },
    );
    cardRefs.current.slice(0, papers.length).forEach((card) => {
      if (card) {
        observer.observe(card);
      }
    });
    return () => observer.disconnect();
  }, [papers]);

  const scrollToIndex = (index: number) => {
    const card = cardRefs.current[index];
    if (!card) {
      return;
    }
    onActiveChange(index);
    card.scrollIntoView({ block: "center", behavior: scrollBehavior() });
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    const keyTargets: Record<string, number> = {
      ArrowDown: Math.min(activeIndex + 1, papers.length - 1),
      ArrowUp: Math.max(activeIndex - 1, 0),
      Home: 0,
      End: papers.length - 1,
    };
    if (event.key in keyTargets && papers.length > 0) {
      event.preventDefault();
      scrollToIndex(keyTargets[event.key]);
    }
  };

  const activeOptionId = papers[activeIndex] ? `paper-option-${papers[activeIndex].paperId}` : undefined;

  return (
    <div className="paper-results">
      <div
        ref={listRef}
        className="paper-results-list"
        role="listbox"
        aria-label="Search results"
        aria-activedescendant={activeOptionId}
        tabIndex={0}
        onKeyDown={handleKeyDown}
      >
        {papers.map((paper, index) => {
          const isActive = index === activeIndex;
          return (
            <div
              key={paper.paperId}
              id={`paper-option-${paper.paperId}`}
              ref={(element) => { cardRefs.current[index] = element; }}
              data-index={index}
              className={`paper-card${isActive ? " active" : ""}`}
              role="option"
              aria-selected={isActive}
              onClick={() => scrollToIndex(index)}
            >
              <span className="paper-card-title">{paper.title}</span>
              <span className="paper-card-meta">
                <span className="paper-card-year">{paper.year ?? "n.d."}</span>
                <span className="paper-card-authors">{formatAuthors(paper.authors, 1)}</span>
                {savedPaperIds.has(paper.paperId) && <span className="paper-card-saved">Saved</span>}
              </span>
            </div>
          );
        })}
        {hasMore && (
          <button
            type="button"
            className="paper-load-more"
            disabled={isLoadingMore}
            onClick={onLoadMore}
          >
            {isLoadingMore ? "Loading…" : "Load more results"}
          </button>
        )}
      </div>
    </div>
  );
}
