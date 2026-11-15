import { useEffect, useRef, useState, type FormEvent } from "react";
import type { ReferencesState } from "../../hooks/useReferences";
import type { CowriterApi } from "../../services/backend/types";
import type { Paper } from "../../types";
import { SearchIcon } from "../ui/Icons";
import { PaperDetail } from "./PaperDetail";
import { PaperResultsList } from "./PaperResultsList";
import { ReferenceLibrary } from "./ReferenceLibrary";

type ResearchMode = "search" | "library";

interface ResearchTabProps {
  api: CowriterApi;
  isActive: boolean;
  references: ReferencesState;
}

export function ResearchTab({ api, isActive, references }: ResearchTabProps) {
  const [mode, setMode] = useState<ResearchMode>("search");
  const [query, setQuery] = useState("");
  const [submittedQuery, setSubmittedQuery] = useState("");
  const [papers, setPapers] = useState<Paper[]>([]);
  const [total, setTotal] = useState(0);
  const [nextOffset, setNextOffset] = useState<number | null>(null);
  const [activeIndex, setActiveIndex] = useState(0);
  const [isSearching, setIsSearching] = useState(false);
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);
  const controllerRef = useRef<AbortController | null>(null);

  useEffect(() => () => controllerRef.current?.abort(), []);

  const runSearch = async (searchQuery: string, offset: number) => {
    controllerRef.current?.abort();
    const controller = new AbortController();
    controllerRef.current = controller;
    if (offset === 0) {
      setIsSearching(true);
    } else {
      setIsLoadingMore(true);
    }
    setSearchError(null);
    try {
      const result = await api.searchPapers(searchQuery, offset, controller.signal);
      setPapers((current) => {
        if (offset === 0) {
          return result.papers;
        }
        const seen = new Set(current.map((paper) => paper.paperId));
        return [...current, ...result.papers.filter((paper) => !seen.has(paper.paperId))];
      });
      setTotal(result.total);
      setNextOffset(result.next);
      if (offset === 0) {
        setActiveIndex(0);
      }
    } catch (error) {
      if (error instanceof Error && error.name === "AbortError") {
        return;
      }
      setSearchError(error instanceof Error ? error.message : "Search failed.");
    } finally {
      if (controllerRef.current === controller) {
        controllerRef.current = null;
        setIsSearching(false);
        setIsLoadingMore(false);
      }
    }
  };

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    const trimmed = query.trim();
    if (!trimmed) {
      return;
    }
    setMode("search");
    setSubmittedQuery(trimmed);
    void runSearch(trimmed, 0);
  };

  const activePaper = papers[activeIndex] ?? null;

  return (
    <div
      id="project-research-panel"
      className="workspace-body research-body"
      role="tabpanel"
      aria-labelledby="project-research-tab"
      hidden={!isActive}
    >
      <div className="research-toolbar">
        <form className="research-search" role="search" onSubmit={handleSubmit}>
          <SearchIcon aria-hidden="true" />
          <input
            type="search"
            placeholder="Search papers on Semantic Scholar…"
            aria-label="Search papers"
            value={query}
            maxLength={300}
            onChange={(event) => setQuery(event.target.value)}
          />
          <button type="submit" disabled={!query.trim() || isSearching}>
            {isSearching ? "Searching…" : "Search"}
          </button>
        </form>
        <div className="segmented" role="group" aria-label="Research view">
          <button
            type="button"
            aria-pressed={mode === "search"}
            className={mode === "search" ? "active" : ""}
            onClick={() => setMode("search")}
          >
            Search
          </button>
          <button
            type="button"
            aria-pressed={mode === "library"}
            className={mode === "library" ? "active" : ""}
            onClick={() => setMode("library")}
          >
            Library <span className="segmented-count">{references.references.length}</span>
          </button>
        </div>
      </div>

      {references.error && <p className="research-error" role="alert">{references.error}</p>}

      {mode === "search" ? (
        <div className="research-search-view">
          {searchError && <p className="research-error" role="alert">{searchError}</p>}
          {papers.length === 0 ? (
            <div className="research-empty">
              {isSearching ? (
                <p>Searching…</p>
              ) : submittedQuery && !searchError ? (
                <>
                  <h2>No papers found</h2>
                  <p>Try broader keywords for “{submittedQuery}”.</p>
                </>
              ) : (
                <>
                  <h2>Find sources for your writing</h2>
                  <p>Search Semantic Scholar, scroll through the results, and save the papers you want to cite.</p>
                </>
              )}
            </div>
          ) : (
            <div className="research-split">
              <div className="research-results-pane">
                <p className="research-result-count">
                  {total.toLocaleString()} results for “{submittedQuery}”
                </p>
                <PaperResultsList
                  papers={papers}
                  activeIndex={activeIndex}
                  savedPaperIds={new Set(references.referenceByPaperId.keys())}
                  hasMore={nextOffset !== null}
                  isLoadingMore={isLoadingMore}
                  onActiveChange={setActiveIndex}
                  onLoadMore={() => {
                    if (nextOffset !== null) {
                      void runSearch(submittedQuery, nextOffset);
                    }
                  }}
                />
              </div>
              <div className="research-detail-pane">
                {activePaper && (
                  <PaperDetail
                    key={activePaper.paperId}
                    paper={activePaper}
                    savedReference={references.referenceByPaperId.get(activePaper.paperId)}
                    isPending={references.pendingPaperIds.has(activePaper.paperId)}
                    onSave={(paper) => void references.save(paper)}
                    onRemove={(reference) => void references.remove(reference)}
                  />
                )}
              </div>
            </div>
          )}
        </div>
      ) : (
        <ReferenceLibrary references={references} />
      )}
    </div>
  );
}
