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

// --- CATEGORIES API ---
export async function fetchCategories() {
    const res = await fetch(`${BASE_URL}/categories`);
    return res.json();
}

export async function addCategory(category) {
    const res = await fetch(`${BASE_URL}/add_category`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(category),
    });
    return res.json();
}

export async function deleteCategory(id) {
    const res = await fetch(`${BASE_URL}/categories/${id}`, {
        method: "DELETE",
    });
    if (!res.ok) throw new Error(`Failed to delete category ${id}`);
    return res.json?.() ?? null;
}
