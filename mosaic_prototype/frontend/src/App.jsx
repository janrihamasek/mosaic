import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Navigate, Route, Routes, useLocation } from 'react-router-dom';
import EntryTable from './components/EntryTable';
import EntryForm from './components/EntryForm';
import ActivityForm from './components/ActivityForm';
import ActivityTable from './components/ActivityTable';
import ActivityDetail from './components/ActivityDetail';
import Today from './components/Today';
import Stats from './components/Stats';
import Notification from './components/Notification';
import LoginForm from './components/LoginForm';
import RegisterForm from './components/RegisterForm';
import LogoutButton from './components/LogoutButton';
import {
  fetchEntries,
  deleteEntry,
  fetchActivities,
  addActivity,
  deleteActivity,
  activateActivity,
  deactivateActivity,
} from './api';
import { styles } from './styles/common';
import { useAuth } from './context/AuthContext';
import { formatError } from './utils/errors';

const DEFAULT_ENTRY_FILTERS = {
  startDate: null,
  endDate: null,
  activity: 'all',
  category: 'all',
};

function Dashboard() {
  const [entries, setEntries] = useState([]);
  const [entriesFilters, setEntriesFilters] = useState(DEFAULT_ENTRY_FILTERS);
  const [activeTab, setActiveTab] = useState(() => localStorage.getItem('mosaic_active_tab') || 'Today');
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
      setNotification((prev) => ({ ...prev, visible: false }));
    }, 4000);
  }, []);

  useEffect(() => () => {
    if (notificationTimerRef.current) {
      clearTimeout(notificationTimerRef.current);
    }
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
      showNotification(`Nepodařilo se načíst aktivity: ${formatError(err)}`, 'error');
    } finally {
      setActivitiesLoading(false);
    }
  }, [showNotification]);

  const fetchEntriesData = useCallback(async (filters) => {
    setEntriesLoading(true);
    try {
      const data = await fetchEntries(filters);
      setEntries(data);
    } catch (err) {
      setEntries([]);
      showNotification(`Nepodařilo se načíst záznamy: ${formatError(err)}`, 'error');
    } finally {
      setEntriesLoading(false);
    }
  }, [showNotification]);

  const applyEntriesFilters = useCallback(async (filters) => {
    const normalized = {
      startDate: filters?.startDate ?? null,
      endDate: filters?.endDate ?? null,
      activity: filters?.activity ?? 'all',
      category: filters?.category ?? 'all',
    };
    setEntries([]);
    setEntriesFilters(normalized);
    await fetchEntriesData(normalized);
  }, [fetchEntriesData]);

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

  useEffect(() => {
    localStorage.setItem('mosaic_active_tab', activeTab);
  }, [activeTab]);

  const tabStyle = useCallback((tabName) => (
    activeTab === tabName
      ? { ...styles.tab, ...styles.tabActive }
      : styles.tab
  ), [activeTab]);

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

      <div style={{ ...styles.rowBetween, marginBottom: 24 }}>
        <h1
          style={{ cursor: 'pointer' }}
          onClick={() => setActiveTab('Today')}
          role="button"
          tabIndex={0}
          onKeyPress={(e) => { if (e.key === 'Enter' || e.key === ' ') setActiveTab('Today'); }}
        >
          🧩 Mosaic
        </h1>
        <LogoutButton />
      </div>

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
            filters={entriesFilters}
          />
          {entriesLoading ? (
            <div style={styles.loadingText}>Načítám záznamy…</div>
          ) : (
            <EntryTable
              entries={entries}
              onDelete={deleteEntry}
              onDataChanged={refreshEntries}
              onNotify={showNotification}
              loading={entriesLoading}
            />
          )}
        </div>
      )}
    </div>
  );
}

function PrivateRoute({ children }) {
  const { isAuthenticated } = useAuth();
  const location = useLocation();
  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }
  return children;
}

export default function App() {
  const { isAuthenticated } = useAuth();
  return (
    <Routes>
      <Route
        path="/login"
        element={isAuthenticated ? <Navigate to="/" replace /> : <LoginForm />}
      />
      <Route
        path="/register"
        element={isAuthenticated ? <Navigate to="/" replace /> : <RegisterForm />}
      />
      <Route
        path="/*"
        element={
          <PrivateRoute>
            <Dashboard />
          </PrivateRoute>
        }
      />
    </Routes>
  );
}
