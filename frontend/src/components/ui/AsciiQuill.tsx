import { useEffect, useMemo, useState, type CSSProperties } from "react";

// A quill and an inkwell. Each object's characters appear from its centre outwards,
// hold, fade, and the reveal starts again.
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
const HOLD_MS = 2600;
const FADE_MS = 700;
const REST_MS = 400;
const CYCLE_MS = REVEAL_MS + HOLD_MS + FADE_MS + REST_MS;

interface Glyph {
  char: string;
  col: number;
  delay: number;
}

type Row = Array<string | Glyph>;

function jitter(row: number, col: number) {
  // Deterministic noise so the reveal shimmers instead of growing as a perfect oval.
  const value = Math.sin(row * 12.9898 + col * 78.233) * 43758.5453;
  return value - Math.floor(value);
}

function buildRows(): Row[] {
  const lines = ART.split("\n");
  const objects = new Map<string, Array<{ row: number; col: number }>>();
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

  const delays = new Map<string, number>();
  for (const cells of objects.values()) {
    const centreRow = cells.reduce((sum, cell) => sum + cell.row, 0) / cells.length;
    const centreCol = cells.reduce((sum, cell) => sum + cell.col, 0) / cells.length;
    const distance = (cell: { row: number; col: number }) =>
      Math.hypot(cell.col - centreCol, (cell.row - centreRow) * CELL_ASPECT);
    const farthest = Math.max(...cells.map(distance));
    for (const cell of cells) {
      // Both objects finish together regardless of their size.
      const progress = (distance(cell) / farthest) * 0.85 + jitter(cell.row, cell.col) * 0.15;
      delays.set(`${cell.row}:${cell.col}`, Math.round(progress * REVEAL_MS));
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
      parts.push({ char, col, delay: delays.get(`${row}:${col}`) ?? 0 });
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
  const [cycle, setCycle] = useState(0);
  const [fading, setFading] = useState(false);

  useEffect(() => {
    const query = window.matchMedia?.("(prefers-reduced-motion: reduce)");
    if (!query) {
      return;
    }
    const update = () => setReduced(query.matches);
    query.addEventListener("change", update);
    return () => query.removeEventListener("change", update);
  }, []);

  useEffect(() => {
    if (reduced) {
      return;
    }
    const fade = window.setTimeout(() => setFading(true), REVEAL_MS + HOLD_MS);
    const restart = window.setTimeout(() => {
      setFading(false);
      setCycle((current) => current + 1);
    }, CYCLE_MS);
    return () => {
      window.clearTimeout(fade);
      window.clearTimeout(restart);
    };
  }, [reduced, cycle]);

  return (
    <pre
      className={`ascii-quill${reduced ? "" : " animated"}${fading ? " fading" : ""} ${className}`}
      role="img"
      aria-label="Cowriter logo: a quill and an inkwell"
    >
      {/* A new key per cycle remounts the glyphs so their CSS reveal plays again. */}
      <span aria-hidden="true" key={cycle}>
        {rows.map((parts, row) => (
          <span key={row}>
            {parts.map((part) =>
              typeof part === "string" ? part : (
                <span
                  key={part.col}
                  className="ascii-quill-glyph"
                  style={{ "--reveal-delay": `${part.delay}ms` } as CSSProperties}
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
