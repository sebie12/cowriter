import { KeyboardEvent, useEffect, useRef, useState } from "react";
import type { ProviderModel } from "../../types/providers";
import { SendIcon } from "../ui/Icons";
import { ModelSelector, type ProviderOption } from "./ModelSelector";

interface ComposerProps {
  hero: boolean;
  isSending: boolean;
  canSend: boolean;
  providers: ProviderOption[];
  activeProviderId: number | null;
  models: ProviderModel[];
  selectedModelId: string | null;
  isModelsLoading: boolean;
  modelsError: string | null;
  onSelectProvider: (id: number) => void;
  onSelectModel: (id: string) => void;
  onSend: (message: string) => void;
  onStop: () => void;
  onOpenSettings: () => void;
}

export function Composer({
  hero,
  isSending,
  canSend,
  providers,
  activeProviderId,
  models,
  selectedModelId,
  isModelsLoading,
  modelsError,
  onSelectProvider,
  onSelectModel,
  onSend,
  onStop,
  onOpenSettings,
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
    if (!message || isSending || !canSend) {
      return;
    }

    onSend(message);
    setValue("");
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault();
      send();
    }
  };

  return (
    <form
      className={`composer-wrap ${hero ? "hero" : ""}`}
      onSubmit={(event) => {
        event.preventDefault();
        send();
      }}
    >
      <div className="composer" data-composer-card>
        <textarea
          ref={textareaRef}
          value={value}
          rows={1}
          aria-label="Message"
          placeholder="Ask Cowriter anything..."
          onChange={(event) => setValue(event.target.value)}
          onKeyDown={handleKeyDown}
        />
        <div className="composer-toolbar">
          <div className="composer-trailing">
            <ModelSelector
              providers={providers}
              activeProviderId={activeProviderId}
              models={models}
              selectedModelId={selectedModelId}
              isLoading={isModelsLoading}
              error={modelsError}
              disabled={isSending}
              onOpenSettings={onOpenSettings}
              onSelectProvider={onSelectProvider}
              onSelectModel={onSelectModel}
            />
            {isSending ? (
              <button className="send-button stop-button" type="button" onClick={onStop} aria-label="Stop response">
                <span aria-hidden="true" />
              </button>
            ) : (
              <button className="send-button" type="submit" disabled={!canSend || !value.trim()} aria-label="Send message">
                <SendIcon />
              </button>
            )}
          </div>
        </div>
      </div>
    </form>
  );
}
