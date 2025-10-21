import React, { useEffect, useState } from 'react';
import EntryTable from './components/EntryTable';
import EntryForm from './components/EntryForm';
import { fetchEntries, addEntry, deleteEntry } from './api';

export default function App() {
    const [entries, setEntries] = useState([]);
    // Přidáváme nový stav pro sledování aktivní karty.
    // Výchozí hodnota je 'Entries'.
    const [activeTab, setActiveTab] = useState('Entries');

    const loadEntries = async () => {
        const data = await fetchEntries();
        setEntries(data);
    };

    const handleSave = async (entry) => {
        await addEntry(entry);
        loadEntries();
    };

    const handleDelete = async (id) => {
        await deleteEntry(id);
        loadEntries();
    };

    useEffect(() => {
        loadEntries();
    }, []);

    // Funkce pro nastavení aktivní karty
    const handleTabChange = (tabName) => {
        setActiveTab(tabName);
    };

    // Styly pro menu a aktivní kartu
    const tabStyle = (tabName) => ({
        padding: '10px 15px',
        cursor: 'pointer',
        borderBottom: activeTab === tabName ? '3px solid #007bff' : '3px solid transparent',
        fontWeight: activeTab === tabName ? 'bold' : 'normal',
        color: activeTab === tabName ? '#007bff' : '#333',
        transition: 'all 0.3s ease',
        textTransform: 'uppercase',
    });

    return (
        <div style={{ maxWidth: "800px", margin: "20px auto", fontFamily: "Segoe UI, sans-serif" }}>
            <h1>🧩 Mosaic – notes </h1>

            {/* Menu se dvěma kartami */}
            <div style={{ display: 'flex', borderBottom: '1px solid #ccc', marginBottom: '20px' }}>
                <div 
                    style={tabStyle('Entries')} 
                    onClick={() => handleTabChange('Entries')}
                >
                    Entries
                </div>
                <div 
                    style={tabStyle('Categories')} 
                    onClick={() => handleTabChange('Categories')}
                >
                    Categories
                </div>
            </div>

            {/* Obsah karet */}
            <div>
                {activeTab === 'Entries' && (
                    <>
                        <EntryForm onSave={handleSave} />
                        <EntryTable entries={entries} onDelete={handleDelete} />
                    </>
                )}

                {activeTab === 'Categories' && (
                    // Karta Categories - prozatím prázdná
                    <div style={{ padding: '20px', border: '1px dashed #ccc', textAlign: 'center' }}>
                        <p>Obsah karty Categories bude brzy k dispozici...</p>
                    </div>
                )}
            </div>
        </div>
    );
}