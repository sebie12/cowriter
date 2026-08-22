import { openUrl } from "@tauri-apps/plugin-opener";

export async function openExternalUrl(url: string): Promise<void> {
  const parsedUrl = new URL(url);
  if (parsedUrl.protocol !== "https:") {
    throw new Error("Authorization URL must use HTTPS.");
  }

  if ("__TAURI_INTERNALS__" in window) {
    await openUrl(url);
    return;
  }

  const openedWindow = window.open(url, "_blank");
  if (!openedWindow) {
    throw new Error("The browser blocked the provider sign-in window.");
  }

  openedWindow.opener = null;
}
