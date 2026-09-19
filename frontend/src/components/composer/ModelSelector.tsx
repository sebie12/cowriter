import { useEffect, useId, useRef, useState } from "react";
import type { ProviderModel } from "../../types/providers";
import { BackIcon, CheckIcon, ChevronDownIcon, ChevronRightIcon } from "../ui/Icons";

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
  onOpenSettings: () => void;
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
  onOpenSettings,
  onSelectProvider,
  onSelectModel,
}: ModelSelectorProps) {
  const [open, setOpen] = useState(false);
  const [pane, setPane] = useState<Pane>("root");
  const rootRef = useRef<HTMLDivElement | null>(null);
  const triggerRef = useRef<HTMLButtonElement | null>(null);
  const lastRootPaneRef = useRef<Exclude<Pane, "root"> | null>(null);
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

  useEffect(() => {
    if (!open) {
      return;
    }
    requestAnimationFrame(() => {
      const preferredItem = pane === "root" && lastRootPaneRef.current
        ? rootRef.current?.querySelector<HTMLElement>(`[data-root-pane='${lastRootPaneRef.current}']`)
        : null;
      (preferredItem ?? rootRef.current?.querySelector<HTMLElement>("[role='menuitem'], [role='menuitemradio']"))?.focus();
    });
  }, [open, pane]);

  const closeMenu = () => {
    setOpen(false);
    setPane("root");
    requestAnimationFrame(() => triggerRef.current?.focus());
  };

  return (
    <div
      ref={rootRef}
      className="model-selector"
      onKeyDown={(event) => {
        if (!open) {
          return;
        }
        if (event.key === "Escape") {
          event.preventDefault();
          if (pane === "root") {
            closeMenu();
          } else {
            setPane("root");
          }
          return;
        }
        if (event.key === "ArrowLeft" && pane !== "root") {
          event.preventDefault();
          setPane("root");
          return;
        }
        if (event.key === "ArrowRight" && pane === "root" && document.activeElement instanceof HTMLButtonElement) {
          event.preventDefault();
          document.activeElement.click();
          return;
        }
        if (event.key === "Tab") {
          window.setTimeout(() => {
            setOpen(false);
            setPane("root");
          }, 0);
          return;
        }
        if (!["ArrowDown", "ArrowUp", "Home", "End"].includes(event.key)) {
          return;
        }
        const items = Array.from(rootRef.current?.querySelectorAll<HTMLElement>("[role='menuitem'], [role='menuitemradio']") ?? []);
        if (items.length === 0) {
          return;
        }
        event.preventDefault();
        const currentIndex = items.indexOf(document.activeElement as HTMLElement);
        const nextIndex = event.key === "Home"
          ? 0
          : event.key === "End"
            ? items.length - 1
            : event.key === "ArrowUp"
              ? (currentIndex - 1 + items.length) % items.length
              : (currentIndex + 1) % items.length;
        items[nextIndex].focus();
      }}
    >
      <button
        ref={triggerRef}
        type="button"
        className="model-selector-trigger"
        aria-haspopup={providers.length > 0 ? "menu" : undefined}
        aria-expanded={providers.length > 0 ? open : undefined}
        aria-controls={open ? menuId : undefined}
        disabled={disabled}
        title={providers.length === 0 ? "Open settings to connect a provider" : modelLabel}
        onClick={() => {
          if (providers.length === 0) {
            onOpenSettings();
            return;
          }
          setPane("root");
          setOpen((current) => !current);
        }}
      >
        <span>{providers.length === 0 ? "Set up provider" : modelLabel}</span>
        <ChevronDownIcon size={12} className={open ? "open" : undefined} />
      </button>

      {open && (
        <div id={menuId} className="model-selector-menu" role="menu">
          {pane === "root" && (
            <>
              <button
                type="button"
                tabIndex={-1}
                className="model-menu-cell"
                role="menuitem"
                aria-haspopup="menu"
                data-root-pane="provider"
                onClick={() => {
                  lastRootPaneRef.current = "provider";
                  setPane("provider");
                }}
              >
                <span>Provider</span>
                <span className="model-menu-value">{activeProvider?.name ?? "Select"}</span>
                <ChevronRightIcon size={14} />
              </button>
              <button
                type="button"
                tabIndex={-1}
                className="model-menu-cell"
                role="menuitem"
                aria-haspopup="menu"
                data-root-pane="model"
                onClick={() => {
                  lastRootPaneRef.current = "model";
                  setPane("model");
                }}
              >
                <span>Model</span>
                <span className="model-menu-value">{modelLabel}</span>
                <ChevronRightIcon size={14} />
              </button>
            </>
          )}

          {pane !== "root" && (
            <button type="button" tabIndex={-1} className="model-menu-cell model-menu-back" role="menuitem" onClick={() => setPane("root")}>
              <BackIcon size={14} />
              <span>Back</span>
            </button>
          )}

          {pane === "provider" && providers.map((provider) => (
            <button
              type="button"
              className="model-menu-option"
              role="menuitemradio"
              tabIndex={-1}
              aria-checked={provider.id === activeProviderId}
              key={provider.id}
              onClick={() => {
                onSelectProvider(provider.id);
                lastRootPaneRef.current = "model";
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
              {isLoading && <div className="model-menu-status" role="status">Loading models...</div>}
              {error && <div className="model-menu-error" role="alert">{error}</div>}
              {!isLoading && !error && models.length === 0 && <div className="model-menu-status" role="status">No models available</div>}
              {!isLoading && models.map((model) => (
                <button
                  type="button"
                  className="model-menu-option"
                  role="menuitemradio"
                  tabIndex={-1}
                  aria-checked={model.id === selectedModelId}
                  key={model.id}
                  onClick={() => {
                    onSelectModel(model.id);
                    closeMenu();
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
