import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import Today from "./components/Today";
import ActivityForm from "./components/ActivityForm";
import ActivityDetail from "./components/ActivityDetail";
import ActivityTable from "./components/ActivityTable";
import EntryForm from "./components/EntryForm";
import EntryTable from "./components/EntryTable";
import Stats from "./components/Stats";
import Notification from "./components/Notification";
import LogoutButton from "./components/LogoutButton";
import { styles } from "./styles/common";
import { useCompactLayout } from "./utils/useBreakpoints";
import { selectIsAuthenticated } from "./store/authSlice";
import { loadEntries, loadStats, loadToday } from "./store/entriesSlice";
import {
  loadActivities,
  selectAllActivities,
  selectActivity,
  selectSelectedActivityId,
} from "./store/activitiesSlice";

const DEFAULT_TAB = "Today";

export default function Dashboard() {
  const dispatch = useDispatch();
  const [activeTab, setActiveTab] = useState(() => localStorage.getItem("mosaic_active_tab") || DEFAULT_TAB);
  const [notification, setNotification] = useState({ message: "", type: "info", visible: false });
  const notificationTimerRef = useRef(null);
  const { isCompact } = useCompactLayout();

  const activities = useSelector(selectAllActivities);
  const selectedActivityId = useSelector(selectSelectedActivityId);
  const isAuthenticated = useSelector(selectIsAuthenticated);

  const selectedActivity = useMemo(
    () => activities.find((activity) => activity.id === selectedActivityId) || null,
    [activities, selectedActivityId]
  );

  const showNotification = useCallback((message, type = "info") => {
    if (!message) return;
    if (notificationTimerRef.current) {
      clearTimeout(notificationTimerRef.current);
    }
    setNotification({ message, type, visible: true });
    notificationTimerRef.current = setTimeout(() => {
      setNotification((prev) => ({ ...prev, visible: false }));
    }, 4000);
  }, []);

  useEffect(
    () => () => {
      if (notificationTimerRef.current) {
        clearTimeout(notificationTimerRef.current);
      }
    },
    []
  );

  useEffect(() => {
    if (typeof window === "undefined") return undefined;
    const handler = (event) => {
      const detail = event?.detail || {};
      if (detail.message) {
        showNotification(detail.message, "error");
      }
    };
    window.addEventListener("mosaic-api-error", handler);
    return () => window.removeEventListener("mosaic-api-error", handler);
  }, [showNotification]);

  useEffect(() => {
    dispatch(loadActivities());
    dispatch(loadEntries());
    dispatch(loadToday());
    dispatch(loadStats());
  }, [dispatch]);

  useEffect(() => {
    localStorage.setItem("mosaic_active_tab", activeTab);
  }, [activeTab]);

  const containerStyle = {
    ...styles.container,
    padding: isCompact ? "1.25rem" : styles.container.padding,
    margin: isCompact ? "1rem auto" : styles.container.margin,
  };

  const headerStyle = {
    display: "flex",
    flexDirection: isCompact ? "column" : "row",
    alignItems: isCompact ? "flex-start" : "center",
    justifyContent: "space-between",
    gap: "0.75rem",
    marginBottom: "1.5rem",
  };

  const toastContainerStyle = {
    ...styles.toastContainer,
    ...(isCompact
      ? {
          left: "50%",
          right: "auto",
          transform: "translateX(-50%)",
        }
      : {}),
  };

  const tabBarStyle = {
    ...styles.tabBar,
    flexWrap: isCompact ? "wrap" : "nowrap",
    gap: "0.5rem",
    overflowX: isCompact ? "auto" : "visible",
    marginBottom: "1.5rem",
  };

  const tabItemStyle = useCallback(
    (tabName) =>
      activeTab === tabName
        ? {
            ...styles.tab,
            ...styles.tabActive,
            flex: isCompact ? "1 0 auto" : "0 0 auto",
            textAlign: "center",
          }
        : {
            ...styles.tab,
            flex: isCompact ? "1 0 auto" : "0 0 auto",
            textAlign: "center",
          },
    [activeTab, isCompact]
  );

  const sectionWrapperStyle = {
    ...styles.cardContainer,
    marginBottom: "1.5rem",
    padding: isCompact ? "1rem" : styles.cardContainer.padding,
  };

  if (!isAuthenticated) {
    return null;
  }

  return (
    <div style={containerStyle}>
      <div style={toastContainerStyle}>
        <Notification
          message={notification.message}
          visible={notification.visible}
          type={notification.type}
        />
      </div>

      <div style={headerStyle}>
        <h1
          style={{ cursor: "pointer", margin: 0 }}
          onClick={() => setActiveTab(DEFAULT_TAB)}
          role="button"
          tabIndex={0}
          onKeyPress={(e) => {
            if (e.key === "Enter" || e.key === " ") setActiveTab(DEFAULT_TAB);
          }}
        >
          🧩 Mosaic
        </h1>
        <LogoutButton />
      </div>

      <div style={tabBarStyle}>
        {["Today", "Activities", "Stats", "Entries"].map((tab) => (
          <div key={tab} style={tabItemStyle(tab)} onClick={() => setActiveTab(tab)}>
            {tab}
          </div>
        ))}
      </div>

      {activeTab === "Today" && (
        <div style={sectionWrapperStyle}>
          <Today onNotify={showNotification} />
        </div>
      )}

      {activeTab === "Activities" && (
        <div style={sectionWrapperStyle}>
          <ActivityForm onNotify={showNotification} />
          {selectedActivity && (
            <ActivityDetail
              activity={selectedActivity}
              onClose={() => dispatch(selectActivity(null))}
              onNotify={showNotification}
            />
          )}
          <ActivityTable
            onNotify={showNotification}
            onOpenDetail={(activity) => dispatch(selectActivity(activity?.id || null))}
          />
        </div>
      )}

      {activeTab === "Stats" && (
        <div style={sectionWrapperStyle}>
          <Stats onNotify={showNotification} />
        </div>
      )}

      {activeTab === "Entries" && (
        <div style={sectionWrapperStyle}>
          <EntryForm onNotify={showNotification} />
          <EntryTable onNotify={showNotification} />
        </div>
      )}
    </div>
  );
}
