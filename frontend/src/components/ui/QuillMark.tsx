// Still line-drawing of the landing page's ASCII quill, for places too small for ASCII art.
export function QuillMark({ className = "" }: { className?: string }) {
  return (
    <svg
      className={`quill-mark ${className}`}
      viewBox="164 106 206 206"
      fill="none"
      stroke="currentColor"
      strokeWidth="13"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M176 118 C 215 128 250 150 262 178 L 270 184 C 279 196 279 210 273 222 C 268 232 263 238 262 242" />
      <path d="M176 118 C 184 138 194 154 204 166 L 212 170 C 210 182 213 194 219 200 L 222 206 C 233 222 247 235 262 242" />
      <path d="M224 164 C 240 184 252 210 262 242 L 270 292" />
      <path
        className="quill-mark-ink"
        d="M268 300 C 280 302 285 292 296 297 C 306 303 312 304 321 298 C 331 291 337 296 345 302 C 350 305 355 306 361 305"
      />
    </svg>
  );
}
