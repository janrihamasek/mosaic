import React, { useCallback, useEffect, useRef, useState } from 'react';
import EntryTable from './components/EntryTable';
import EntryForm from './components/EntryForm';
import { fetchEntries, addEntry, deleteEntry } from './api';
import ActivityForm from './components/ActivityForm';
import ActivityTable from './components/ActivityTable';
import ActivityDetail from './components/ActivityDetail';
import Today from './components/Today';
import { fetchActivities, addActivity, deleteActivity, activateActivity, deactivateActivity } from './api';
import { styles } from './styles/common';
import Notification from './components/Notification';
import CsvImportButton from './components/CsvImportButton';

export default function App() {
  const [entries, setEntries] = useState([]);
  const [activeTab, setActiveTab] = useState('Today');
  const [activeActivities, setActiveActivities] = useState([]);
  const [allActivities, setAllActivities] = useState([]);
  const [selectedActivity, setSelectedActivity] = useState(null);
  const [notification, setNotification] = useState({ message: '', type: 'info', visible: false });
  const notificationTimerRef = useRef(null);
  const [entriesLoading, setEntriesLoading] = useState(false);
  const [activitiesLoading, setActivitiesLoading] = useState(false);

  const showNotification = useCallback((message, type = 'info') => {
    if (!message) return;
    if (notificationTimerRef.current) {
      clearTimeout(notificationTimerRef.current);
    }
    setNotification({ message, type, visible: true });
    notificationTimerRef.current = setTimeout(() => {
      setNotification(prev => ({ ...prev, visible: false }));
    }, 4000);
  }, []);

  useEffect(() => {
    return () => {
      if (notificationTimerRef.current) {
        clearTimeout(notificationTimerRef.current);
      }
    };
  }, []);

  const loadEntries = useCallback(async () => {
    setEntriesLoading(true);
    try {
      const data = await fetchEntries();
      setEntries(data);
    } catch (err) {
      showNotification(`Failed to load entries: ${err.message}`, 'error');
    } finally {
      setEntriesLoading(false);
    }
  }, [showNotification]);

  const loadActivities = useCallback(async () => {
    setActivitiesLoading(true);
    try {
      const [onlyActive, all] = await Promise.all([
        fetchActivities({ all: false }),
        fetchActivities({ all: true }),
      ]);
      setActiveActivities(onlyActive);
      setAllActivities(all);
    } catch (err) {
      showNotification(`Failed to load activities: ${err.message}`, 'error');
    } finally {
      setActivitiesLoading(false);
    }
  }, [showNotification]);

  const refreshAll = useCallback(async () => {
    await Promise.all([loadEntries(), loadActivities()]);
  }, [loadEntries, loadActivities]);

  useEffect(() => {
    loadEntries();
    loadActivities();
  }, [loadEntries, loadActivities]);

  const tabStyle = (tabName) =>
    activeTab === tabName
      ? { ...styles.tab, ...styles.tabActive }
      : styles.tab;

  return (
    <div style={styles.container}>
      <div style={styles.toastContainer}>
        <Notification
          message={notification.message}
          visible={notification.visible}
          type={notification.type}
        />
      </div>

      <h1>🧩 Mosaic</h1>

      <div style={styles.tabBar}>
        <div style={tabStyle('Today')} onClick={() => setActiveTab('Today')}>Today</div>
        <div style={tabStyle('Entries')} onClick={() => setActiveTab('Entries')}>Entries</div>
        <div style={tabStyle('Activities')} onClick={() => setActiveTab('Activities')}>Activities</div>
      </div>

      {activeTab === 'Today' && (
        <div style={styles.cardContainer}>
          <Today onDataChanged={refreshAll} onNotify={showNotification} />
        </div>
      )}

      {activeTab === 'Entries' && (
        <div style={styles.cardContainer}>
          <EntryForm
            onSave={addEntry}
            onDataChanged={refreshAll}
            activities={activeActivities}
            onNotify={showNotification}
          />
          <div style={{ ...styles.flexRow, justifyContent: "flex-end", marginBottom: 12 }}>
            <CsvImportButton onImported={refreshAll} onNotify={showNotification} />
          </div>
          <EntryTable
            entries={entries}
            onDelete={deleteEntry}
            onDataChanged={refreshAll}
            onNotify={showNotification}
            loading={entriesLoading}
          />
        </div>
      )}

      {activeTab === 'Activities' && (
        <div style={styles.cardContainer}>
          <ActivityForm onSave={addActivity} onDataChanged={refreshAll} onNotify={showNotification} />
          {selectedActivity && (
            <ActivityDetail
              activity={selectedActivity}
              onClose={() => setSelectedActivity(null)}
              onNotify={showNotification}
            />
          )}
          <ActivityTable
            activities={allActivities}
            onActivate={activateActivity}
            onDeactivate={deactivateActivity}
            onDelete={deleteActivity}
            onOpenDetail={setSelectedActivity}
            onDataChanged={refreshAll}
            onNotify={showNotification}
            loading={activitiesLoading}
          />
        </div>
      )}
    </div>
  );
}
