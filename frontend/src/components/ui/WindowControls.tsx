import { useEffect, useState } from "react";
import { getCurrentWindow } from "@tauri-apps/api/window";
import { closeWindow, isTauriWindow, minimizeWindow, toggleMaximizeWindow } from "../../services/appWindow";

function MinimizeGlyph() {
  return (
    <svg viewBox="0 0 10 10" width="10" height="10" aria-hidden="true">
      <path d="M1 5h8" stroke="currentColor" strokeWidth="1" />
    </svg>
  );
}

function MaximizeGlyph() {
  return (
    <svg viewBox="0 0 10 10" width="10" height="10" fill="none" aria-hidden="true">
      <rect x="1.5" y="1.5" width="7" height="7" rx="1" stroke="currentColor" strokeWidth="1" />
    </svg>
  );
}

function RestoreGlyph() {
  return (
    <svg viewBox="0 0 10 10" width="10" height="10" fill="none" aria-hidden="true">
      <rect x="1.5" y="3.5" width="5" height="5" rx="1" stroke="currentColor" strokeWidth="1" />
      <path d="M3.5 3.5V2.5a1 1 0 0 1 1-1h3a1 1 0 0 1 1 1v3a1 1 0 0 1-1 1h-1" stroke="currentColor" strokeWidth="1" />
    </svg>
  );
}

function CloseGlyph() {
  return (
    <svg viewBox="0 0 10 10" width="10" height="10" aria-hidden="true">
      <path d="m1.5 1.5 7 7m0-7-7 7" stroke="currentColor" strokeWidth="1" strokeLinecap="round" />
    </svg>
  );
}

/** Minimize / maximize / close, pinned to the top-right corner of the app. */
export function WindowControls() {
  const [isMaximized, setIsMaximized] = useState(false);

  useEffect(() => {
    if (!isTauriWindow()) {
      return;
    }
    const appWindow = getCurrentWindow();
    let disposed = false;
    let unlisten: (() => void) | null = null;
    const sync = () => {
      void appWindow.isMaximized().then((maximized) => {
        if (!disposed) {
          setIsMaximized(maximized);
        }
      }).catch(() => undefined);
    };

    sync();
    void appWindow.onResized(sync).then((stop) => {
      if (disposed) {
        stop();
      } else {
        unlisten = stop;
      }
    }).catch(() => undefined);

    return () => {
      disposed = true;
      unlisten?.();
    };
  }, []);

  if (!isTauriWindow()) {
    return null;
  }

  return (
    <div className="window-controls" role="group" aria-label="Window controls">
      <button type="button" className="window-control" aria-label="Minimize" title="Minimize" onClick={minimizeWindow}>
        <MinimizeGlyph />
      </button>
      <button
        type="button"
        className="window-control"
        aria-label={isMaximized ? "Restore" : "Maximize"}
        title={isMaximized ? "Restore" : "Maximize"}
        onClick={toggleMaximizeWindow}
      >
        {isMaximized ? <RestoreGlyph /> : <MaximizeGlyph />}
      </button>
      <button type="button" className="window-control close" aria-label="Close" title="Close" onClick={closeWindow}>
        <CloseGlyph />
      </button>
    </div>
  );
}
