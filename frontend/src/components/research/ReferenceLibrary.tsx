import { useMemo, useState } from "react";
import type { ReferencesState } from "../../hooks/useReferences";
import type { Reference } from "../../types";
import { formatAuthors, PaperDetail } from "./PaperDetail";

type SortKey = "title" | "authors" | "year" | "venue" | "citations" | "added";

const COLUMNS: Array<{ key: SortKey; label: string; className: string }> = [
  { key: "title", label: "Title", className: "col-title" },
  { key: "authors", label: "Authors", className: "col-authors" },
  { key: "year", label: "Year", className: "col-year" },
  { key: "venue", label: "Published in", className: "col-venue" },
  { key: "citations", label: "Cited by", className: "col-citations" },
  { key: "added", label: "Added", className: "col-added" },
];

function sortValue(reference: Reference, key: SortKey): string | number {
  switch (key) {
    case "title":
      return reference.title.toLowerCase();
    case "authors":
      return (reference.authors[0] ?? "").toLowerCase();
    case "year":
      return reference.year ?? -Infinity;
    case "venue":
      return (reference.venue ?? "").toLowerCase();
    case "citations":
      return reference.citationCount ?? -Infinity;
    case "added":
      return reference.createdAt;
  }
}

function formatAdded(value: string) {
  const date = new Date(value.endsWith("Z") || value.includes("+") ? value : `${value}Z`);
  return Number.isNaN(date.getTime())
    ? ""
    : date.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
}

interface ReferenceLibraryProps {
  references: ReferencesState;
}

export function ReferenceLibrary({ references }: ReferenceLibraryProps) {
  const [sortKey, setSortKey] = useState<SortKey>("added");
  const [ascending, setAscending] = useState(false);
  const [query, setQuery] = useState("");
  const [selectedId, setSelectedId] = useState<number | null>(null);

  const rows = useMemo(() => {
    const needle = query.trim().toLowerCase();
    const filtered = needle
      ? references.references.filter((reference) => [
          reference.title,
          reference.venue ?? "",
          reference.year ? String(reference.year) : "",
          ...reference.authors,
        ].some((value) => value.toLowerCase().includes(needle)))
      : references.references;
    return [...filtered].sort((first, second) => {
      const a = sortValue(first, sortKey);
      const b = sortValue(second, sortKey);
      const order = a < b ? -1 : a > b ? 1 : 0;
      return ascending ? order : -order;
    });
  }, [references.references, query, sortKey, ascending]);

  const selected = references.references.find((reference) => reference.id === selectedId) ?? null;

  const toggleSort = (key: SortKey) => {
    if (key === sortKey) {
      setAscending((value) => !value);
    } else {
      setSortKey(key);
      setAscending(key === "title" || key === "authors" || key === "venue");
    }
  };

  return (
    <div className={`reference-library${selected ? " has-selection" : ""}`}>
      <div className="reference-table-pane">
        <div className="reference-toolbar">
          <span className="reference-count">
            {references.references.length} {references.references.length === 1 ? "reference" : "references"}
          </span>
          <input
            type="search"
            className="reference-filter"
            placeholder="Filter by title, author, year…"
            aria-label="Filter references"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
        </div>
        {references.isLoading ? (
          <p className="research-empty">Loading references…</p>
        ) : references.references.length === 0 ? (
          <div className="research-empty">
            <h2>No saved references yet</h2>
            <p>Search for papers and select <strong>Save to references</strong>. The proofreader checks your claims against them.</p>
          </div>
        ) : (
          <div className="reference-table-scroll">
            <table className="reference-table">
              <thead>
                <tr>
                  {COLUMNS.map((column) => (
                    <th
                      key={column.key}
                      className={column.className}
                      aria-sort={sortKey === column.key ? (ascending ? "ascending" : "descending") : "none"}
                    >
                      <button type="button" onClick={() => toggleSort(column.key)}>
                        {column.label}
                        <span className="sort-indicator" aria-hidden="true">
                          {sortKey === column.key ? (ascending ? "▲" : "▼") : ""}
                        </span>
                      </button>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rows.map((reference) => (
                  <tr
                    key={reference.id}
                    className={reference.id === selectedId ? "selected" : ""}
                    aria-selected={reference.id === selectedId}
                    tabIndex={0}
                    onClick={() => setSelectedId(reference.id === selectedId ? null : reference.id)}
                    onKeyDown={(event) => {
                      if (event.key === "Enter" || event.key === " ") {
                        event.preventDefault();
                        setSelectedId(reference.id === selectedId ? null : reference.id);
                      }
                    }}
                  >
                    <td className="col-title">{reference.title}</td>
                    <td className="col-authors">{formatAuthors(reference.authors, 2)}</td>
                    <td className="col-year">{reference.year ?? "—"}</td>
                    <td className="col-venue">{reference.venue ?? "—"}</td>
                    <td className="col-citations">{reference.citationCount?.toLocaleString() ?? "—"}</td>
                    <td className="col-added">{formatAdded(reference.createdAt)}</td>
                  </tr>
                ))}
                {rows.length === 0 && (
                  <tr className="reference-no-match">
                    <td colSpan={COLUMNS.length}>No references match “{query}”.</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>
      {selected && (
        <div className="research-detail-pane">
          <button
            type="button"
            className="research-detail-close"
            aria-label="Close details"
            onClick={() => setSelectedId(null)}
          >
            ×
          </button>
          <PaperDetail
            paper={selected}
            savedReference={selected}
            isPending={references.pendingPaperIds.has(selected.paperId)}
            onSave={(paper) => void references.save(paper)}
            onRemove={(reference) => {
              setSelectedId(null);
              void references.remove(reference);
            }}
          />
        </div>
      )}
    </div>
  );
}
