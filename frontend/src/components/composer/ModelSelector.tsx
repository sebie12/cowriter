import { useEffect, useId, useRef, useState } from "react";
import type { ProviderModel } from "../../types/providers";
import { CheckIcon, ChevronDownIcon, ChevronRightIcon } from "../ui/Icons";

export interface ProviderOption {
  id: number;
  name: string;
  detail: string;
}

interface ModelSelectorProps {
  providers: ProviderOption[];
  activeProviderId: number | null;
  models: ProviderModel[];
  selectedModelId: string | null;
  isLoading: boolean;
  error: string | null;
  disabled: boolean;
  onSelectProvider: (id: number) => void;
  onSelectModel: (id: string) => void;
}

type Pane = "root" | "provider" | "model";

export function ModelSelector({
  providers,
  activeProviderId,
  models,
  selectedModelId,
  isLoading,
  error,
  disabled,
  onSelectProvider,
  onSelectModel,
}: ModelSelectorProps) {
  const [open, setOpen] = useState(false);
  const [pane, setPane] = useState<Pane>("root");
  const rootRef = useRef<HTMLDivElement | null>(null);
  const menuId = useId();
  const activeProvider = providers.find((provider) => provider.id === activeProviderId) ?? null;
  const selectedModel = models.find((model) => model.id === selectedModelId) ?? null;
  const modelLabel = selectedModel?.name ?? selectedModel?.id ?? (isLoading ? "Loading models..." : "Select model");

  useEffect(() => {
    if (!open) {
      return;
    }
    const closeOutside = (event: MouseEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) {
        setOpen(false);
        setPane("root");
      }
    };
    document.addEventListener("mousedown", closeOutside);
    return () => document.removeEventListener("mousedown", closeOutside);
  }, [open]);

  return (
    <div
      ref={rootRef}
      className="model-selector"
      onKeyDown={(event) => {
        if (event.key !== "Escape" || !open) {
          return;
        }
        event.preventDefault();
        if (pane === "root") {
          setOpen(false);
        } else {
          setPane("root");
        }
      }}
    >
      <button
        type="button"
        className="model-selector-trigger"
        aria-haspopup="menu"
        aria-expanded={open}
        aria-controls={open ? menuId : undefined}
        disabled={disabled || providers.length === 0}
        title={modelLabel}
        onClick={() => {
          setPane("root");
          setOpen((current) => !current);
        }}
      >
        <span>{modelLabel}</span>
        <ChevronDownIcon size={12} className={open ? "open" : undefined} />
      </button>

      {open && (
        <div id={menuId} className="model-selector-menu" role="menu">
          {pane === "root" && (
            <>
              <button type="button" className="model-menu-cell" role="menuitem" onClick={() => setPane("provider")}>
                <span>Provider</span>
                <span className="model-menu-value">{activeProvider?.name ?? "Select"}</span>
                <ChevronRightIcon size={14} />
              </button>
              <button type="button" className="model-menu-cell" role="menuitem" onClick={() => setPane("model")}>
                <span>Model</span>
                <span className="model-menu-value">{modelLabel}</span>
                <ChevronRightIcon size={14} />
              </button>
            </>
          )}

          {pane === "provider" && providers.map((provider) => (
            <button
              type="button"
              className="model-menu-option"
              role="menuitemradio"
              aria-checked={provider.id === activeProviderId}
              key={provider.id}
              onClick={() => {
                onSelectProvider(provider.id);
                setPane("model");
              }}
            >
              <span className="model-option-copy">
                <strong>{provider.name}</strong>
                <small>{provider.detail}</small>
              </span>
              {provider.id === activeProviderId && <CheckIcon />}
            </button>
          ))}

          {pane === "model" && (
            <>
              {isLoading && <div className="model-menu-status">Loading models...</div>}
              {error && <div className="model-menu-error">{error}</div>}
              {!isLoading && !error && models.length === 0 && <div className="model-menu-status">No models available</div>}
              {!isLoading && models.map((model) => (
                <button
                  type="button"
                  className="model-menu-option"
                  role="menuitemradio"
                  aria-checked={model.id === selectedModelId}
                  key={model.id}
                  onClick={() => {
                    onSelectModel(model.id);
                    setOpen(false);
                    setPane("root");
                  }}
                >
                  <span className="model-option-copy"><strong>{model.name ?? model.id}</strong></span>
                  {model.id === selectedModelId && <CheckIcon />}
                </button>
              ))}
            </>
          )}
        </div>
      )}
    </div>
  );
}
