import React, { useEffect, useState } from 'react';
import EntryTable from './components/EntryTable';
import EntryForm from './components/EntryForm';
import { fetchEntries, addEntry } from './api';

export default function App() {
    const [entries, setEntries] = useState([]);

    const loadEntries = async () => {
        const data = await fetchEntries();
        setEntries(data);
    };

    const handleSave = async (entry) => {
        await addEntry(entry);
        loadEntries();
    };

    useEffect(() => {
        loadEntries();
    }, []);

    return (
        <div style={{ maxWidth: "800px", margin: "20px auto", fontFamily: "Segoe UI, sans-serif" }}>
            <h1>🧩 Mosaic – osobní záznamy</h1>
            <EntryForm onSave={handleSave} />
            <EntryTable entries={entries} />
        </div>
    );
}
