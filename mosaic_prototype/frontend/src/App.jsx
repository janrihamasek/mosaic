import React, { useEffect, useState } from 'react';
import EntryTable from './components/EntryTable';
import EntryForm from './components/EntryForm';
import { fetchEntries, addEntry, deleteEntry } from './api';
import ActivityForm from './components/ActivityForm';
import ActivityTable from './components/ActivityTable';
import ActivityDetail from './components/ActivityDetail';
import Today from './components/Today';
import { fetchActivities, addActivity, deleteActivity, activateActivity, deactivateActivity } from './api';

export default function App() {
  const [entries, setEntries] = useState([]);
  const [activeTab, setActiveTab] = useState('Today'); // default Today
  const [activeActivities, setActiveActivities] = useState([]);
  const [allActivities, setAllActivities] = useState([]);
  const [selectedActivity, setSelectedActivity] = useState(null);

  const loadEntries = async () => {
    const data = await fetchEntries();
    setEntries(data);
  };

  const loadActivities = async () => {
    const [onlyActive, all] = await Promise.all([
      fetchActivities({ all: false }),
      fetchActivities({ all: true }),
    ]);
    setActiveActivities(onlyActive);
    setAllActivities(all);
  };

  useEffect(() => {
    loadEntries();
    loadActivities();
  }, []);

  const handleSave = async (entry) => {
    await addEntry(entry);
    await loadEntries();
  };

  const handleDelete = async (id) => {
    await deleteEntry(id);
    await loadEntries();
  };

  const handleSaveActivity = async (activity) => {
    await addActivity(activity);
    await loadActivities();
  };

  const handleDeleteActivity = async (id) => {
    await deleteActivity(id);
    await loadActivities();
  };

  const handleDeactivateActivity = async (id) => {
    await deactivateActivity(id);
    await loadActivities();
  };

  const handleActivateActivity = async (id) => {
    await activateActivity(id);
    await loadActivities();
  };

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
    <div style={{ maxWidth: "900px", margin: "20px auto", fontFamily: "Segoe UI, sans-serif" }}>
      <h1>🧩 Mosaic</h1>

      <div style={{ display: 'flex', borderBottom: '1px solid #ccc', marginBottom: '20px' }}>
        <div style={tabStyle('Today')} onClick={() => setActiveTab('Today')}>Today</div>
        <div style={tabStyle('Entries')} onClick={() => setActiveTab('Entries')}>Entries</div>
        <div style={tabStyle('Activities')} onClick={() => setActiveTab('Activities')}>Activities</div>
      </div>

      {activeTab === 'Today' && <Today onDataChanged={loadEntries} />}

      {activeTab === 'Entries' && (
        <>
          <EntryForm onSave={handleSave} activities={activeActivities} />
          <EntryTable entries={entries} onDelete={handleDelete} />
        </>
      )}

      {activeTab === 'Activities' && (
        <>
          <ActivityForm onSave={handleSaveActivity} />
          {selectedActivity && (
            <ActivityDetail activity={selectedActivity} onClose={() => setSelectedActivity(null)} />
          )}
          <ActivityTable
            activities={allActivities}
            onActivate={handleActivateActivity}
            onDeactivate={handleDeactivateActivity}
            onDelete={handleDeleteActivity}
            onOpenDetail={(a) => setSelectedActivity(a)}
          />
        </>
      )}
    </div>
  );
}
