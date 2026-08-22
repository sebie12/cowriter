import { KeyboardEvent, useEffect, useRef, useState } from "react";
import type { ProviderModel } from "../../types/providers";

interface ComposerProps {
  disabled: boolean;
  models: ProviderModel[];
  selectedModelId: string | null;
  hasModelConnection: boolean;
  isModelsLoading: boolean;
  modelsError: string | null;
  onSelectModel: (modelId: string) => void;
  onSend: (message: string) => void;
}

export function Composer({
  disabled,
  models,
  selectedModelId,
  hasModelConnection,
  isModelsLoading,
  modelsError,
  onSelectModel,
  onSend,
}: ComposerProps) {
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
    if (!message || disabled || isModelsLoading || !selectedModelId) {
      return;
    }

    onSend(message);
    setValue("");
  };

  const modelPlaceholder = !hasModelConnection
    ? "Connect Ollama"
    : isModelsLoading
      ? "Loading models..."
      : modelsError
        ? "Models unavailable"
        : "No models installed";

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
          <select
            className="composer-model-select"
            aria-label="Language model"
            title={modelsError ?? "Select an Ollama model"}
            value={selectedModelId ?? ""}
            disabled={disabled || isModelsLoading || !hasModelConnection || models.length === 0}
            onChange={(event) => onSelectModel(event.target.value)}
          >
            {!selectedModelId && <option value="">{modelPlaceholder}</option>}
            {models.map((model) => (
              <option value={model.id} key={model.id}>{model.name ?? model.id}</option>
            ))}
          </select>
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
        <button className="send-button" type="submit" disabled={disabled || !selectedModelId || !value.trim()}>
          {disabled ? "Thinking..." : "Send"}
        </button>
      </div>
      <p className="composer-hint" id="composer-hint" role={isModelsLoading ? "status" : undefined}>
        {modelsError ? `Model error: ${modelsError}` : "Enter sends. Shift + Enter adds a new line."}
      </p>
    </form>
  );
}
