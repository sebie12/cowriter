import { getCurrentWindow } from "@tauri-apps/api/window";
import type { MouseEvent as ReactMouseEvent } from "react";

/**
 * The native title bar is turned off (`decorations: false` in tauri.conf.json),
 * so the app draws its own window controls and drag regions. Everything here is
 * a no-op in a plain browser, where the browser owns the window.
 */
export function isTauriWindow(): boolean {
  return "__TAURI_INTERNALS__" in window;
}

function report(action: string) {
  return (error: unknown) => console.error(`Failed to ${action} window`, error);
}

export function minimizeWindow(): void {
  void getCurrentWindow().minimize().catch(report("minimize"));
}

export function toggleMaximizeWindow(): void {
  void getCurrentWindow().toggleMaximize().catch(report("maximize"));
}

export function closeWindow(): void {
  void getCurrentWindow().close().catch(report("close"));
}

// Presses on these stay with the control instead of moving the window.
const INTERACTIVE_SELECTOR = "button, a, input, select, textarea, label, [role='button'], [role='tab'], [contenteditable='true']";

/**
 * Mouse-down handler for title-bar-like surfaces: dragging moves the window and
 * double-clicking toggles maximize, unless the press lands on a control.
 */
export function handleWindowDragMouseDown(event: ReactMouseEvent<HTMLElement>): void {
  if (!isTauriWindow() || event.button !== 0) {
    return;
  }
  if (event.target instanceof Element && event.target.closest(INTERACTIVE_SELECTOR)) {
    return;
  }
  event.preventDefault();
  if (event.detail === 2) {
    toggleMaximizeWindow();
    return;
  }
  void getCurrentWindow().startDragging().catch(report("drag"));
}
