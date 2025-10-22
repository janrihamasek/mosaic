const BASE_URL = "http://127.0.0.1:5000";

// --- ENTRIES API ---
export async function fetchEntries() {
    const res = await fetch(`${BASE_URL}/entries`);
    return res.json();
}

export async function addEntry(entry) {
    const res = await fetch(`${BASE_URL}/add_entry`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(entry),
    });
    return res.json();
}

export async function deleteEntry(id) {
    const res = await fetch(`${BASE_URL}/entries/${id}`, {
        method: 'DELETE',
    });
    if (!res.ok) throw new Error(`Failed to delete entry ${id}`);
    return res.json?.() ?? null;
}

// --- ACTIVITIES API ---
export async function fetchActivities() {
    const res = await fetch(`${BASE_URL}/activities`);
    return res.json();
}

export async function addActivity(activity) {
    const res = await fetch(`${BASE_URL}/add_activity`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(activity),
    });
    return res.json();
}

export async function deleteActivity(id) {
    const res = await fetch(`${BASE_URL}/activities/${id}`, {
        method: "DELETE",
    });
    if (!res.ok) throw new Error(`Failed to delete activity ${id}`);
    return res.json?.() ?? null;
}
