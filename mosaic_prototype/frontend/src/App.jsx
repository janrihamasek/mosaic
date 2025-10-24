import React, { useEffect, useState } from 'react';
import EntryTable from './components/EntryTable';
import EntryForm from './components/EntryForm';
import { fetchEntries, addEntry, deleteEntry } from './api';
import ActivityForm from './components/ActivityForm';
import ActivityTable from './components/ActivityTable';
import ActivityDetail from './components/ActivityDetail';
import Today from './components/Today';
import { fetchActivities, addActivity, deleteActivity, activateActivity, deactivateActivity } from './api';
import { styles } from './styles/common';

export default function App() {
  const [entries, setEntries] = useState([]);
  const [activeTab, setActiveTab] = useState('Today');
  const [activeActivities, setActiveActivities] = useState([]);
  const [allActivities, setAllActivities] = useState([]);
  const [selectedActivity, setSelectedActivity] = useState(null);

  const loadEntries = async () => setEntries(await fetchEntries());
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

  const tabStyle = (tabName) =>
    activeTab === tabName
      ? { ...styles.tab, ...styles.tabActive }
      : styles.tab;

  return (
    <div style={styles.container}>
      <h1>🧩 Mosaic</h1>

      <div style={styles.tabBar}>
        <div style={tabStyle('Today')} onClick={() => setActiveTab('Today')}>Today</div>
        <div style={tabStyle('Entries')} onClick={() => setActiveTab('Entries')}>Entries</div>
        <div style={tabStyle('Activities')} onClick={() => setActiveTab('Activities')}>Activities</div>
      </div>

      {activeTab === 'Today' && <Today onDataChanged={loadEntries} />}
      {activeTab === 'Entries' && (
        <>
          <EntryForm onSave={addEntry} activities={activeActivities} />
          <EntryTable entries={entries} onDelete={deleteEntry} />
        </>
      )}
      {activeTab === 'Activities' && (
        <>
          <ActivityForm onSave={addActivity} />
          {selectedActivity && (
            <ActivityDetail activity={selectedActivity} onClose={() => setSelectedActivity(null)} />
          )}
          <ActivityTable
            activities={allActivities}
            onActivate={activateActivity}
            onDeactivate={deactivateActivity}
            onDelete={deleteActivity}
            onOpenDetail={setSelectedActivity}
          />
        </>
      )}
    </div>
  );
}
