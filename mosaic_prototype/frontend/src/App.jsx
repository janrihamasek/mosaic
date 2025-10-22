import React, { useEffect, useState } from 'react';
import EntryTable from './components/EntryTable';
import EntryForm from './components/EntryForm';
import { fetchEntries, addEntry, deleteEntry } from './api';
import ActivityForm from './components/ActivityForm';
import ActivityTable from './components/ActivityTable';
import { fetchActivities, addActivity, deleteActivity } from './api';


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

    const [activities, setActivities] = useState([]);

    const loadActivities = async () => {
        const data = await fetchActivities();
        setActivities(data);
    };

    const handleSaveActivity = async (activity) => {
        await addActivity(activity);
        loadActivities();
    };

    const handleDeleteActivity = async (id) => {
        await deleteActivity(id);
        loadActivities();
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
                    style={tabStyle('Activities')} 
                    onClick={() => handleTabChange('Activities')}
                >
                    Activities
                </div>
            </div>

            {/* Obsah karet */}
            <div>
                {activeTab === 'Entries' && (
                    <>
                        <EntryForm onSave={handleSave} activities={activities} />
                        <EntryTable entries={entries} onDelete={handleDelete} />
                    </>
                )}

                {activeTab === 'Activities' && (
                    <>
                        <ActivityForm onSave={handleSaveActivity} />
                        <ActivityTable activities={activities} onDelete={handleDeleteActivity} />
                    </>
                )}
            </div>
        </div>
    );
}