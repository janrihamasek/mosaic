import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import EntryTable from './components/EntryTable';
import EntryForm from './components/EntryForm';
import { fetchEntries, deleteEntry } from './api';
import ActivityForm from './components/ActivityForm';
import ActivityTable from './components/ActivityTable';
import ActivityDetail from './components/ActivityDetail';
import Today from './components/Today';
import Stats from './components/Stats';
import { fetchActivities, addActivity, deleteActivity, activateActivity, deactivateActivity } from './api';
import { styles } from './styles/common';
import Notification from './components/Notification';

const DEFAULT_ENTRY_FILTERS = {
  startDate: null,
  endDate: null,
  activity: "all",
  category: "all",
};

export default function App() {
  const [entries, setEntries] = useState([]);
  const [entriesFilters, setEntriesFilters] = useState(DEFAULT_ENTRY_FILTERS);
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

  const fetchEntriesData = useCallback(
    async (filters) => {
      setEntriesLoading(true);
      try {
        const data = await fetchEntries(filters);
        setEntries(data);
      } catch (err) {
        setEntries([]);
        showNotification(`Failed to load entries: ${err.message}`, 'error');
      } finally {
        setEntriesLoading(false);
      }
    },
    [showNotification]
  );

  const applyEntriesFilters = useCallback(
    async (filters) => {
      const normalized = {
        startDate: filters?.startDate ?? null,
        endDate: filters?.endDate ?? null,
        activity: filters?.activity ?? 'all',
        category: filters?.category ?? 'all',
      };
      setEntries([]);
      setEntriesFilters(normalized);
      await fetchEntriesData(normalized);
    },
    [fetchEntriesData]
  );

  const refreshEntries = useCallback(async () => {
    await fetchEntriesData(entriesFilters);
  }, [fetchEntriesData, entriesFilters]);

  const refreshAll = useCallback(async () => {
    await Promise.all([refreshEntries(), loadActivities()]);
  }, [refreshEntries, loadActivities]);

  useEffect(() => {
    loadActivities();
  }, [loadActivities]);

  useEffect(() => {
    applyEntriesFilters(DEFAULT_ENTRY_FILTERS);
  }, [applyEntriesFilters]);

  const tabStyle = (tabName) =>
    activeTab === tabName
      ? { ...styles.tab, ...styles.tabActive }
      : styles.tab;

  const categoryOptions = useMemo(() => {
    const unique = new Set();
    allActivities.forEach((activity) => {
      const category = activity?.category?.trim();
      if (category) unique.add(category);
    });
    entries.forEach((entry) => {
      const category = entry?.category?.trim();
      if (category) unique.add(category);
    });
    return Array.from(unique);
  }, [allActivities, entries]);

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
        <div style={tabStyle('Activities')} onClick={() => setActiveTab('Activities')}>Activities</div>
        <div style={tabStyle('Stats')} onClick={() => setActiveTab('Stats')}>Stats</div>
        <div style={tabStyle('Entries')} onClick={() => setActiveTab('Entries')}>Entries</div>
      </div>

      {activeTab === 'Today' && (
        <div style={styles.cardContainer}>
          <Today onDataChanged={refreshAll} onNotify={showNotification} />
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
              onDataChanged={refreshAll}
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

      {activeTab === 'Stats' && (
        <div style={styles.cardContainer}>
          <Stats onNotify={showNotification} />
        </div>
      )}

      {activeTab === 'Entries' && (
        <div style={styles.cardContainer}>
          <EntryForm
            activities={allActivities}
            categories={categoryOptions}
            onApplyFilters={applyEntriesFilters}
            onNotify={showNotification}
            onImported={refreshAll}
          />
          <EntryTable
            entries={entries}
            onDelete={deleteEntry}
            onDataChanged={refreshEntries}
            onNotify={showNotification}
            loading={entriesLoading}
          />
        </div>
      )}

    </div>
  );
}
