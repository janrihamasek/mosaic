import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Navigate, Route, Routes, useLocation } from 'react-router-dom';
import { useDispatch, useSelector } from 'react-redux';
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
import { styles } from './styles/common';
import { selectIsAuthenticated } from './store/authSlice';
import { loadEntries, loadStats, loadToday } from './store/entriesSlice';
import {
  loadActivities,
  selectAllActivities,
  selectActivity,
  selectSelectedActivityId,
} from './store/activitiesSlice';

const DEFAULT_TAB = 'Today';

function Dashboard() {
  const dispatch = useDispatch();
  const [activeTab, setActiveTab] = useState(() => localStorage.getItem('mosaic_active_tab') || DEFAULT_TAB);
  const [notification, setNotification] = useState({ message: '', type: 'info', visible: false });
  const notificationTimerRef = useRef(null);

  const activities = useSelector(selectAllActivities);
  const selectedActivityId = useSelector(selectSelectedActivityId);
  const selectedActivity = useMemo(
    () => activities.find((activity) => activity.id === selectedActivityId) || null,
    [activities, selectedActivityId]
  );

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

  useEffect(() => {
    if (typeof window === 'undefined') return undefined;
    const handler = (event) => {
      const detail = event?.detail || {};
      if (detail.message) {
        showNotification(detail.message, 'error');
      }
    };
    window.addEventListener('mosaic-api-error', handler);
    return () => window.removeEventListener('mosaic-api-error', handler);
  }, [showNotification]);

  useEffect(() => {
    dispatch(loadActivities());
    dispatch(loadEntries());
    dispatch(loadToday());
    dispatch(loadStats());
  }, [dispatch]);

  useEffect(() => {
    localStorage.setItem('mosaic_active_tab', activeTab);
  }, [activeTab]);

  const tabStyle = useCallback((tabName) => (
    activeTab === tabName
      ? { ...styles.tab, ...styles.tabActive }
      : styles.tab
  ), [activeTab]);

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
          onClick={() => setActiveTab(DEFAULT_TAB)}
          role="button"
          tabIndex={0}
          onKeyPress={(e) => { if (e.key === 'Enter' || e.key === ' ') setActiveTab(DEFAULT_TAB); }}
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
          <Today onNotify={showNotification} />
        </div>
      )}

      {activeTab === 'Activities' && (
        <div style={styles.cardContainer}>
          <ActivityForm onNotify={showNotification} />
          {selectedActivity && (
            <ActivityDetail
              activity={selectedActivity}
              onClose={() => dispatch(selectActivity(null))}
              onNotify={showNotification}
            />
          )}
          <ActivityTable onNotify={showNotification} onOpenDetail={(activity) => dispatch(selectActivity(activity?.id || null))} />
        </div>
      )}

      {activeTab === 'Stats' && (
        <div style={styles.cardContainer}>
          <Stats onNotify={showNotification} />
        </div>
      )}

      {activeTab === 'Entries' && (
        <div style={styles.cardContainer}>
          <EntryForm onNotify={showNotification} />
          <EntryTable onNotify={showNotification} />
        </div>
      )}
    </div>
  );
}

function PrivateRoute({ children }) {
  const isAuthenticated = useSelector(selectIsAuthenticated);
  const location = useLocation();
  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }
  return children;
}

export default function App() {
  const isAuthenticated = useSelector(selectIsAuthenticated);
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
