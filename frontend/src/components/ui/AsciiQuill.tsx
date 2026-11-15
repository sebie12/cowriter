import { useEffect, useMemo, useState, type CSSProperties } from "react";

// A quill and an inkwell. Each object's characters appear once, from its centre outwards;
// afterwards a highlight keeps travelling around each object's outline.
const ART = String.raw`
                                            .=+**::
                                         .*-.:%@==+:
                                      -===-+@%*=-*-
                                   .*-+.:#%+-.:-*.
                                .-*-::-**=...=++.
                               #-=-.=*@*=-==-:.
                             ++-:+#+%*=---+*-
                           --+-.-#*+-.:-=##
                         -=+:--#+*=:..:=++
                       .*+=.=#%%@+...:=##.
                      *-:.:#*+#+:..::-=+.
                    .#--::=*%#+-...:=++
                   +=--:-*+%+-...:=+#=
                 .=%+-:+*#*+:...:=#%:
                :*:.:=#:@#*-.::-:-*#
              .-:-..=%=%+=....-+#@*
             .+#--.=+#*=-....-=*=
            :==:-:#=%+------=#+-
            *++-=***=:....-+#@:
           -:-+*:#+-..-+++*-:
         ...-++-@*-:..:+==.
          ::+:*#-..==+=.
          .=:#++::..
          -:+. .:.
         :--     .
        :--                ..-=---.
      .:-=                .%@#-:+@@@=
     .+#=                 -@*=-=++*@#
     -:#                  *:--++*#**@:
    ::#.                 :=:==##@@@@@-
   -:+.                  =.::...=*=#@%
   :+                   ::::...:-*-+#@-
  +=.                   =.:....:=+=-*@%
 -=.                   .-*+:..:==#+#@@*
.-.                      .-+%#***##%*:`.slice(1);

// The inkwell sits in the lower right; everything else belongs to the quill.
const INKWELL_TOP_ROW = 25;
const INKWELL_LEFT_COL = 20;
// Character cells are roughly twice as tall as they are wide.
const CELL_ASPECT = 2;

const REVEAL_MS = 2200;
// Matches the length of the ascii-quill-reveal animation in styles.css.
const GLYPH_REVEAL_MS = 900;
// Matches the ascii-quill-shimmer animation; one lap around each outline.
const SHIMMER_MS = 4800;

interface Glyph {
  char: string;
  col: number;
  revealDelay: number;
  // Only outline characters keep animating, starting at their place along the lap.
  shimmerDelay: number | null;
}

type Row = Array<string | Glyph>;

interface Cell {
  row: number;
  col: number;
}

function jitter(row: number, col: number) {
  // Deterministic noise so the reveal shimmers instead of growing as a perfect oval.
  const value = Math.sin(row * 12.9898 + col * 78.233) * 43758.5453;
  return value - Math.floor(value);
}

function buildRows(): Row[] {
  const lines = ART.split("\n");
  const isBlank = (row: number, col: number) => (lines[row]?.[col] ?? " ") === " ";
  const objects = new Map<string, Cell[]>();
  lines.forEach((line, row) => {
    [...line].forEach((char, col) => {
      if (char === " ") {
        return;
      }
      const key = row >= INKWELL_TOP_ROW && col >= INKWELL_LEFT_COL ? "inkwell" : "quill";
      const cells = objects.get(key) ?? [];
      cells.push({ row, col });
      objects.set(key, cells);
    });
  });

  const revealDelays = new Map<string, number>();
  const shimmerDelays = new Map<string, number>();
  const shimmerStart = REVEAL_MS + GLYPH_REVEAL_MS;
  for (const cells of objects.values()) {
    const centreRow = cells.reduce((sum, cell) => sum + cell.row, 0) / cells.length;
    const centreCol = cells.reduce((sum, cell) => sum + cell.col, 0) / cells.length;
    const offset = (cell: Cell) => [cell.col - centreCol, (cell.row - centreRow) * CELL_ASPECT] as const;
    const distance = (cell: Cell) => Math.hypot(...offset(cell));
    const farthest = Math.max(...cells.map(distance));
    for (const cell of cells) {
      const key = `${cell.row}:${cell.col}`;
      // Both objects finish together regardless of their size.
      const progress = (distance(cell) / farthest) * 0.85 + jitter(cell.row, cell.col) * 0.15;
      revealDelays.set(key, Math.round(progress * REVEAL_MS));

      const onOutline = isBlank(cell.row - 1, cell.col) || isBlank(cell.row + 1, cell.col)
        || isBlank(cell.row, cell.col - 1) || isBlank(cell.row, cell.col + 1);
      if (onOutline) {
        // Position along the lap = angle around the object's centre, clockwise from the top.
        const [x, y] = offset(cell);
        const turn = (Math.atan2(x, -y) / (2 * Math.PI) + 1) % 1;
        shimmerDelays.set(key, Math.round(shimmerStart + turn * SHIMMER_MS));
      }
    }
  }

  return lines.map((line, row) => {
    const parts: Row = [];
    let gap = "";
    [...line].forEach((char, col) => {
      if (char === " ") {
        gap += char;
        return;
      }
      if (gap) {
        parts.push(gap);
        gap = "";
      }
      const key = `${row}:${col}`;
      parts.push({
        char,
        col,
        revealDelay: revealDelays.get(key) ?? 0,
        shimmerDelay: shimmerDelays.get(key) ?? null,
      });
    });
    return parts;
  });
}

function prefersReducedMotion() {
  return typeof window !== "undefined"
    && window.matchMedia?.("(prefers-reduced-motion: reduce)").matches === true;
}

export function AsciiQuill({ className = "" }: { className?: string }) {
  const rows = useMemo(buildRows, []);
  const [reduced, setReduced] = useState(prefersReducedMotion);

  useEffect(() => {
    const query = window.matchMedia?.("(prefers-reduced-motion: reduce)");
    if (!query) {
      return;
    }
    const update = () => setReduced(query.matches);
    query.addEventListener("change", update);
    return () => query.removeEventListener("change", update);
  }, []);

  return (
    <pre
      className={`ascii-quill${reduced ? "" : " animated"} ${className}`}
      role="img"
      aria-label="Cowriter logo: a quill and an inkwell"
    >
      <span aria-hidden="true">
        {rows.map((parts, row) => (
          <span key={row}>
            {parts.map((part) =>
              typeof part === "string" ? part : (
                <span
                  key={part.col}
                  className={`ascii-quill-glyph${part.shimmerDelay === null ? "" : " outline"}`}
                  style={{
                    "--reveal-delay": `${part.revealDelay}ms`,
                    ...(part.shimmerDelay === null ? {} : { "--shimmer-delay": `${part.shimmerDelay}ms` }),
                  } as CSSProperties}
                >
                  {part.char}
                </span>
              ),
            )}
            {row < rows.length - 1 ? "\n" : null}
          </span>
        ))}
      </span>
    </pre>
  );
}
