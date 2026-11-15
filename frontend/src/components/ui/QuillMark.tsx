// Still line drawing of the quill from the landing page's ASCII logo (without the inkwell),
// for places too small for ASCII art.
export function QuillMark({ className = "" }: { className?: string }) {
  return (
    <svg
      className={`quill-mark ${className}`}
      viewBox="-6 -3 66 74"
      fill="none"
      stroke="currentColor"
      strokeWidth="5"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M46 3 C 50 1 54 1 53 6 C 48 18 40 30 29 40 C 23 45 17 47 12 47 C 13 39 22 24 46 3 Z" />
      {/* One side of the feather is solid, the other left open. */}
      <path fill="currentColor" d="M12 47 C 13 39 22 24 46 3 C 43 13 27 31 12 47 Z" />
      <path d="M12 47 L 3 68" />
    </svg>
  );
}
