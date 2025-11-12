import { initHealthConnect, syncNow } from "./healthconnect_sync";

const HEALTH_CONNECT_DEVICE_ID = "mosaic-healthconnect-device";

function resolveBackendUrl() {
  if (typeof window === "undefined") {
    return "https://api.mosaic.local";
  }
  return (
    (window as Window & { __MOSAIC_API_URL__?: string }).__MOSAIC_API_URL__ ||
    `${window.location.origin}`
  );
}

async function jwtProvider(): Promise<string> {
  if (typeof window === "undefined") {
    return "";
  }
  const token = window.localStorage.getItem("mosaic_access_token");
  if (token) {
    return token;
  }
  console.warn("[HealthConnect] JWT token missing, request may fail until user logs in.");
  return "";
}

function createSyncButton() {
  if (typeof document === "undefined") {
    return;
  }
  const existing = document.getElementById("healthconnect-sync");
  if (existing) {
    return;
  }
  const button = document.createElement("button");
  button.id = "healthconnect-sync";
  button.innerText = "Sync Wearable";
  button.style.position = "fixed";
  button.style.bottom = "1rem";
  button.style.right = "1rem";
  button.style.zIndex = "9999";
  button.style.padding = "0.5rem 0.9rem";
  button.style.borderRadius = "0.6rem";
  button.style.border = "none";
  button.style.backgroundColor = "#3a7bd5";
  button.style.color = "#fff";
  button.style.boxShadow = "0 4px 12px rgba(0,0,0,0.25)";

  button.addEventListener("click", () => {
    button.disabled = true;
    button.innerText = "Syncing…";
    void syncNow().finally(() => {
      button.disabled = false;
      button.innerText = "Sync Wearable";
    });
  });
  document.body.appendChild(button);
}

function listenForConnectivity() {
  if (typeof window === "undefined") {
    return;
  }
  window.addEventListener("online", () => {
    console.info("[HealthConnect] Device back online, triggering sync");
    void syncNow();
  });
}

function bootstrap() {
  initHealthConnect({
    backendUrl: resolveBackendUrl(),
    deviceId: window?.localStorage.getItem("mosaic_device_id") || HEALTH_CONNECT_DEVICE_ID,
    jwtProvider,
    autoSyncIntervalMs: 1000 * 60 * 5,
  });
  createSyncButton();
  listenForConnectivity();
  void syncNow();
}

if (typeof window !== "undefined") {
  if (document.readyState === "complete") {
    bootstrap();
  } else {
    window.addEventListener("load", bootstrap);
  }
}
