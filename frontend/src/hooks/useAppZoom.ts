import { useEffect } from "react";
import { getCurrentWebview } from "@tauri-apps/api/webview";

const STORAGE_KEY = "cowriter.zoom";
const ZOOM_STEPS = [0.5, 0.67, 0.75, 0.8, 0.9, 1, 1.1, 1.25, 1.5, 1.75, 2];
const DEFAULT_ZOOM = 1;

function isTauriRuntime(): boolean {
  return "__TAURI_INTERNALS__" in window;
}

function readStoredZoom(): number {
  try {
    const stored = Number(window.localStorage.getItem(STORAGE_KEY));
    return ZOOM_STEPS.includes(stored) ? stored : DEFAULT_ZOOM;
  } catch {
    return DEFAULT_ZOOM;
  }
}

function storeZoom(zoom: number): void {
  try {
    window.localStorage.setItem(STORAGE_KEY, String(zoom));
  } catch {
    // Zoom still applies for this session if storage is unavailable.
  }
}

function nextZoom(current: number, direction: 1 | -1): number {
  const index = ZOOM_STEPS.indexOf(current);
  const nextIndex = Math.min(ZOOM_STEPS.length - 1, Math.max(0, index + direction));
  return ZOOM_STEPS[nextIndex];
}

/**
 * Scales the whole desktop app with Ctrl/Cmd + "+", Ctrl/Cmd + "-" and
 * Ctrl/Cmd + "0" (reset), and remembers the level across launches. Uses the
 * native webview zoom, so layout and editor coordinates stay correct. In a
 * plain browser the browser's own zoom already handles these keys.
 */
export function useAppZoom(): void {
  useEffect(() => {
    if (!isTauriRuntime()) {
      return;
    }

    const webview = getCurrentWebview();
    let zoom = readStoredZoom();

    const apply = (value: number) => {
      zoom = value;
      storeZoom(value);
      webview.setZoom(value).catch((error: unknown) => {
        console.error("Failed to set app zoom", error);
      });
    };

    if (zoom !== DEFAULT_ZOOM) {
      apply(zoom);
    }

    const handleKeyDown = (event: KeyboardEvent) => {
      if (!(event.ctrlKey || event.metaKey) || event.altKey) {
        return;
      }
      let target: number | null = null;
      if (event.key === "+" || event.key === "=" || event.code === "NumpadAdd") {
        target = nextZoom(zoom, 1);
      } else if (event.key === "-" || event.key === "_" || event.code === "NumpadSubtract") {
        target = nextZoom(zoom, -1);
      } else if (event.key === "0" || event.code === "Numpad0") {
        target = DEFAULT_ZOOM;
      }
      if (target === null) {
        return;
      }
      event.preventDefault();
      if (target !== zoom) {
        apply(target);
      }
    };

    window.addEventListener("keydown", handleKeyDown, { capture: true });
    return () => window.removeEventListener("keydown", handleKeyDown, { capture: true });
  }, []);
}
