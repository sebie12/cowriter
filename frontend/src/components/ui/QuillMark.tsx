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
      <path d="M47 2 C 52 1 54 3 52 7 C 47 18 40 30 29 40 C 23 45 17 47 12 47 C 13 39 22 24 47 2 Z" />
      <path d="M44 7 C 34 20 22 34 12 47 L 3 68" />
    </svg>
  );
}
