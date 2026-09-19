import { useEffect, type RefObject } from "react";

const FOCUSABLE_SELECTOR = [
  "a[href]",
  "button:not([disabled])",
  "input:not([disabled])",
  "select:not([disabled])",
  "textarea:not([disabled])",
  "[contenteditable='true']",
  "[tabindex]:not([tabindex='-1'])",
].join(",");

export function useDialogFocus(
  dialogRef: RefObject<HTMLElement | null>,
  initialFocusRef: RefObject<HTMLElement | null>,
) {
  useEffect(() => {
    const dialog = dialogRef.current;
    const previousFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    if (!dialog) {
      return;
    }

    const modalLayer = dialog.closest<HTMLElement>(".settings-overlay");
    const backgroundElements = modalLayer?.parentElement
      ? Array.from(modalLayer.parentElement.children).filter((element): element is HTMLElement => (
          element instanceof HTMLElement && element !== modalLayer
        ))
      : [];
    const previousInertValues = backgroundElements.map((element) => element.inert);
    backgroundElements.forEach((element) => { element.inert = true; });

    const focusableElements = () => Array.from(dialog.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR))
      .filter((element) => {
        const style = window.getComputedStyle(element);
        return element.getClientRects().length > 0 && style.visibility !== "hidden" && style.display !== "none";
      });

    (initialFocusRef.current ?? focusableElements()[0] ?? dialog).focus();

    const containFocus = (event: KeyboardEvent) => {
      if (event.key !== "Tab") {
        return;
      }
      const elements = focusableElements();
      if (elements.length === 0) {
        event.preventDefault();
        dialog.focus();
        return;
      }

      const first = elements[0];
      const last = elements[elements.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };

    dialog.addEventListener("keydown", containFocus);
    return () => {
      dialog.removeEventListener("keydown", containFocus);
      backgroundElements.forEach((element, index) => { element.inert = previousInertValues[index]; });
      if (previousFocus?.isConnected) {
        previousFocus.focus();
      } else {
        document.querySelector<HTMLElement>("[data-dialog-fallback-focus]")?.focus();
      }
    };
  }, [dialogRef, initialFocusRef]);
}
