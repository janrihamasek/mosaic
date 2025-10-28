const DEFAULT_BASE_URL = "http://127.0.0.1:5000";
const TEST_BASE_URL = "http://127.0.0.1:5000";

const getBaseUrl = () => {
  const envUrl = process.env.REACT_APP_API_BASE_URL;
  if (envUrl && envUrl.trim().length > 0) {
    return envUrl.trim().replace(/\/+$/, "");
  }
  if (process.env.NODE_ENV === "test") {
    return TEST_BASE_URL;
  }
  return DEFAULT_BASE_URL;
};

const BASE_URL = getBaseUrl();

async function request(path, options) {
  const res = await fetch(`${BASE_URL}${path}`, options);
  const contentType = res.headers?.get("content-type") || "";
  const isJson = contentType.includes("application/json");
  let payload = null;

  if (isJson) {
    try {
      payload = await res.json();
    } catch (err) {
      payload = null;
    }
  } else {
    payload = await res.text();
  }

  if (!res.ok) {
    const message =
      (payload && typeof payload === "object" && payload.error) ||
      (typeof payload === "string" && payload.trim().length > 0 ? payload : null) ||
      res.statusText ||
      "Request failed";
    throw new Error(message);
  }

  return payload;
}

// --- ENTRIES ---
export async function fetchEntries(filters = {}) {
  const params = new URLSearchParams();
  if (filters?.startDate) params.set("start_date", filters.startDate);
  if (filters?.endDate) params.set("end_date", filters.endDate);
  if (filters?.activity && filters.activity !== "all") params.set("activity", filters.activity);
  if (filters?.category && filters.category !== "all") params.set("category", filters.category);
  const qs = params.toString();
  return request(`/entries${qs ? `?${qs}` : ""}`);
}

export async function addEntry(entry) {
  return request("/add_entry", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(entry),
  });
}

export async function deleteEntry(id) {
  return request(`/entries/${id}`, { method: "DELETE" });
}

// --- ACTIVITIES ---
export async function fetchActivities({ all = false } = {}) {
  return request(`/activities${all ? "?all=true" : ""}`);
}

export async function addActivity(activity) {
  return request("/add_activity", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(activity),
  });
}

export async function updateActivity(id, payload) {
  return request(`/activities/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function deactivateActivity(id) {
  return request(`/activities/${id}/deactivate`, { method: "PATCH" });
}

export async function activateActivity(id) {
  return request(`/activities/${id}/activate`, { method: "PATCH" });
}

export async function deleteActivity(id) {
  return request(`/activities/${id}`, { method: "DELETE" });
}

// --- STATS ---
export async function fetchProgressStats({ group = "activity", period = 30, date } = {}) {
  const params = new URLSearchParams();
  if (group) params.set("group", group);
  if (period) params.set("period", String(period));
  if (date) params.set("date", date);
  const qs = params.toString();
  return request(`/stats/progress${qs ? `?${qs}` : ""}`);
}

// --- TODAY ---
export async function fetchToday(dateStr) {
  const qs = dateStr ? `?date=${encodeURIComponent(dateStr)}` : "";
  return request(`/today${qs}`);
}

export async function finalizeDay(dateStr) {
  return request("/finalize_day", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ date: dateStr }),
  });
}

// --- IMPORT ---
export async function importEntriesCsv(file) {
  const formData = new FormData();
  formData.append("file", file);
  return request("/import_csv", {
    method: "POST",
    body: formData,
  });
}
