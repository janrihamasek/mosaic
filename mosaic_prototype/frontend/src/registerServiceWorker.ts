import { Workbox } from "workbox-window";

const SW_PATH = `${process.env.PUBLIC_URL || ""}/service-worker.js`;

const isLocalhost = () =>
  Boolean(
    window.location.hostname === "localhost" ||
      window.location.hostname === "127.0.0.1" ||
      window.location.hostname === "::1"
  );

const canUseServiceWorker = () =>
  "serviceWorker" in navigator && (window.isSecureContext || isLocalhost());

export function registerServiceWorker(): Workbox | null {
  if (process.env.NODE_ENV !== "production" || !canUseServiceWorker()) {
    return null;
  }

  const workbox = new Workbox(SW_PATH, { scope: "/" });

  workbox.addEventListener("activated", (event) => {
    if (!event.isUpdate) {
      console.info("[Mosaic] PWA cache ready for offline use.");
    }
  });

  workbox.addEventListener("waiting", () => {
    console.info("[Mosaic] New version available; it will activate after all tabs close.");
  });

  workbox
    .register()
    .then((registration) => {
      registration.addEventListener("updatefound", () => {
        const newWorker = registration.installing;
        if (!newWorker) {
          return;
        }
        newWorker.addEventListener("statechange", () => {
          if (newWorker.state === "installed" && navigator.serviceWorker?.controller) {
            console.info("[Mosaic] New version available");
          }
        });
      });
    })
    .catch((error) => {
      console.error("[Mosaic] Failed to register service worker", error);
    });

  return workbox;
}

export async function updatePWA(): Promise<void> {
  if (typeof navigator === "undefined" || !("serviceWorker" in navigator)) {
    return;
  }

  try {
    const registrations = await navigator.serviceWorker.getRegistrations();
    await Promise.all(registrations.map((registration) => registration.update()));
  } catch (error) {
    console.error("[Mosaic] Failed to update service worker", error);
  }

  if (typeof window !== "undefined") {
    window.location.reload();
  }
}

export function unregisterServiceWorker(): void {
  if ("serviceWorker" in navigator) {
    navigator.serviceWorker
      .getRegistrations()
      .then((registrations) => registrations.forEach((registration) => registration.unregister()))
      .catch(() => {
        /* ignore */
      });
  }
}
