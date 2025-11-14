const DEFAULT_BASE_URL = "https://10.0.1.31:5001";
const TEST_BASE_URL = "https://10.0.1.31:5001";

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
export const API_BACKEND_LABEL =
  (process.env.REACT_APP_BACKEND_LABEL && process.env.REACT_APP_BACKEND_LABEL.trim()) ||
  (API_BASE_URL.includes("localhost:5001") || API_BASE_URL.includes("127.0.0.1:5001")
    ? "Production API"
    : API_BASE_URL.includes("localhost") || API_BASE_URL.includes("127.0.0.1")
      ? "Development API"
      : API_BASE_URL);
