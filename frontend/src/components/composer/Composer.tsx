import { KeyboardEvent, useEffect, useRef, useState } from "react";

interface ComposerProps {
  disabled: boolean;
  canSend: boolean;
  onSend: (message: string) => void;
}

export function Composer({ disabled, canSend, onSend }: ComposerProps) {
  const [value, setValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);

  useEffect(() => {
    const textarea = textareaRef.current;
    if (!textarea) {
      return;
    }

    textarea.style.height = "auto";
    textarea.style.height = `${Math.min(textarea.scrollHeight, 180)}px`;
  }, [value]);

  const send = () => {
    const message = value.trim();
    if (!message || disabled || !canSend) {
      return;
    }

    onSend(message);
    setValue("");
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      send();
    }
  };

  return (
    <form
      className="composer-wrap"
      onSubmit={(event) => {
        event.preventDefault();
        send();
      }}
    >
      <div className="composer">
        <div className="composer-controls">
          <button className="composer-tool-button" type="button" title="Attach files">
            +
          </button>
        </div>
        <textarea
          ref={textareaRef}
          value={value}
          disabled={disabled}
          rows={1}
          aria-label="Message"
          aria-describedby="composer-hint"
          placeholder="Ask about your writing or research..."
          onChange={(event) => setValue(event.target.value)}
          onKeyDown={handleKeyDown}
        />
        <button className="send-button" type="submit" disabled={disabled || !canSend || !value.trim()}>
          {disabled ? "Thinking..." : "Send"}
        </button>
      </div>
      <p className="composer-hint" id="composer-hint">Enter sends. Shift + Enter adds a new line.</p>
    </form>
  );
}
