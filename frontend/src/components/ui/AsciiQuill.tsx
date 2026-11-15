import { useEffect, useState } from "react";

// The quill is drawn once; only the ink line beneath the nib animates.
const QUILL = [
  "         @ @ @ @ @ @ @ @ @",
  "    @ @ @            @ @ @ @ @",
  "  @ @                         @ @",
  "  @             @ @ @ @         @",
  "@ @ @ @ @ @     @      @ @ @ @ @ @",
  "        @ @ @ @ @           @ @ @ @",
  "              @ @ @ @        @ @ @ @ @",
  "                     @ @ @ @ @      @ @ @ @",
].join("\n");
const NIB = "                                           @";
const INK = "~".repeat(18);

const STEP_MS = 85;
const HOLD_MS = 2600;
const FADE_MS = 700;
const REST_MS = 500;

type Phase = "drawing" | "holding" | "fading";

function prefersReducedMotion() {
  return typeof window !== "undefined"
    && window.matchMedia?.("(prefers-reduced-motion: reduce)").matches === true;
}

export function AsciiQuill({ className = "" }: { className?: string }) {
  const [reduced, setReduced] = useState(prefersReducedMotion);
  const [drawn, setDrawn] = useState(() => (prefersReducedMotion() ? INK.length : 0));
  const [phase, setPhase] = useState<Phase>("drawing");

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
      setDrawn(INK.length);
      setPhase("holding");
      return;
    }
    let timer: number;
    if (phase === "drawing") {
      timer = window.setTimeout(() => {
        if (drawn < INK.length) {
          setDrawn(drawn + 1);
        } else {
          setPhase("holding");
        }
      }, drawn === 0 ? REST_MS : STEP_MS);
    } else if (phase === "holding") {
      timer = window.setTimeout(() => setPhase("fading"), HOLD_MS);
    } else {
      timer = window.setTimeout(() => {
        setDrawn(0);
        setPhase("drawing");
      }, FADE_MS);
    }
    return () => window.clearTimeout(timer);
  }, [reduced, phase, drawn]);

  const isDrawing = phase === "drawing" && drawn > 0 && drawn < INK.length;
  const settled = INK.slice(0, isDrawing ? drawn - 1 : drawn);
  const head = isDrawing ? INK[drawn - 1] : "";
  const pending = INK.slice(drawn);

  return (
    <pre className={`ascii-quill ${className}`} role="img" aria-label="Cowriter logo: a quill drawing a line">
      <span aria-hidden="true">
        {QUILL}
        {"\n"}
        {NIB}
        <span className={`ascii-quill-ink${phase === "fading" ? " fading" : ""}`}>
          {settled}
          {head && <span className="ascii-quill-head">{head}</span>}
        </span>
        {/* Keeps the block's width fixed while the line is still being drawn. */}
        <span className="ascii-quill-pending">{pending}</span>
      </span>
    </pre>
  );
}
