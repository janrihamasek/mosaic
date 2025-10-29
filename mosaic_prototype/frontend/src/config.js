const DEFAULT_BASE_URL = "http://127.0.0.1:5000";
const TEST_BASE_URL = "http://127.0.0.1:5000";

export function getBaseUrl() {
  const envUrl = process.env.REACT_APP_API_BASE_URL;
  if (envUrl && envUrl.trim().length > 0) {
    return envUrl.trim().replace(/\/+$|^\/+/, "");
  }
  if (process.env.NODE_ENV === "test") {
    return TEST_BASE_URL;
  }
  return DEFAULT_BASE_URL;
}

export const API_BASE_URL = getBaseUrl();
