const BASE_URL = "http://127.0.0.1:5000";

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
