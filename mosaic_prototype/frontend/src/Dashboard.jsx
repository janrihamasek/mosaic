import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useDispatch, useSelector } from "react-redux";

import Today from "./components/Today";
import ActivityForm from "./components/ActivityForm";
import ActivityDetail from "./components/ActivityDetail";
import ActivityTable from "./components/ActivityTable";
import EntryForm from "./components/EntryForm";
import EntryTable from "./components/EntryTable";
import Stats from "./components/Stats";
import Admin from "./components/Admin";
import Notification from "./components/Notification";
import LogoutButton from "./components/LogoutButton";
import { styles } from "./styles/common";
import { useCompactLayout } from "./utils/useBreakpoints";
import { selectIsAuthenticated } from "./store/authSlice";
import { loadEntries, loadStats, loadToday, setTodayDate } from "./store/entriesSlice";
import {
  loadActivities,
  selectAllActivities,
  selectActivity,
  selectSelectedActivityId,
} from "./store/activitiesSlice";
import { API_BACKEND_LABEL, API_BASE_URL } from "./config";

const DEFAULT_TAB = "Today";
const TABS = ["Today", "Activities", "Stats", "Entries", "Admin"];
const TAB_LABELS = {
  Today: "Today",
  Activities: "Activities",
  Stats: "Stats",
  Entries: "Entries",
  Admin: "Admin",
};

const getTodayIso = () => {
  const now = new Date();
  const tzOffset = now.getTimezoneOffset();
  const adjusted = new Date(now.getTime() - tzOffset * 60000);
  return adjusted.toISOString().slice(0, 10);
};

function resolveInitialTab(initialTab) {
  if (initialTab && TABS.includes(initialTab)) {
    return initialTab;
  }
  if (typeof window !== "undefined") {
    const stored = window.localStorage.getItem("mosaic_active_tab");
    if (stored && TABS.includes(stored)) {
      return stored;
    }
  }
  return DEFAULT_TAB;
}

export default function Dashboard({ initialTab = DEFAULT_TAB }) {
  const dispatch = useDispatch();
  const [activeTab, setActiveTab] = useState(() => resolveInitialTab(initialTab));
  const [tabRenderKeys, setTabRenderKeys] = useState(() =>
    Object.fromEntries(TABS.map((tab) => [tab, 0]))
  );
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
    if (typeof window !== "undefined") {
      window.localStorage.setItem("mosaic_active_tab", activeTab);
    }
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

  const titleWrapperStyle = {
    display: "flex",
    flexDirection: "column",
    gap: "0.3rem",
  };

  const backendBadgeStyle = {
    alignSelf: isCompact ? "flex-start" : "flex-start",
    display: "inline-flex",
    alignItems: "center",
    gap: "0.35rem",
    fontSize: "0.75rem",
    fontWeight: 600,
    color: "#1e3a8a",
    backgroundColor: "#e0e7ff",
    borderRadius: "999px",
    padding: "0.25rem 0.65rem",
    letterSpacing: "0.015em",
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

  const refreshTab = useCallback(
    (tabName) => {
      if (tabName === "Today") {
        const todayIso = getTodayIso();
        dispatch(setTodayDate(todayIso));
        dispatch(loadToday(todayIso));
        dispatch(loadStats({ date: todayIso }));
      } else if (tabName === "Entries") {
        dispatch(
          loadEntries({
            startDate: null,
            endDate: null,
            activity: "all",
            category: "all",
          })
        );
      }

      setTabRenderKeys((prev) => ({
        ...prev,
        [tabName]: (prev?.[tabName] ?? 0) + 1,
      }));
    },
    [dispatch]
  );

  const handleTabSelect = useCallback(
    (tabName) => {
      refreshTab(tabName);
      setActiveTab((prev) => (prev === tabName ? prev : tabName));
    },
    [refreshTab]
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
        <div style={titleWrapperStyle}>
          <h1
            style={{ cursor: "pointer", margin: 0 }}
            onClick={() => handleTabSelect(DEFAULT_TAB)}
            role="button"
            tabIndex={0}
            onKeyPress={(e) => {
              if (e.key === "Enter" || e.key === " ") handleTabSelect(DEFAULT_TAB);
            }}
          >
            🧩 Mosaic
          </h1>
          <span style={backendBadgeStyle} title={`Aktuální API: ${API_BASE_URL}`}>
            🔌 {API_BACKEND_LABEL}
          </span>
        </div>
        <LogoutButton />
      </div>

      <div style={tabBarStyle}>
        {TABS.map((tab) => (
          <div key={tab} style={tabItemStyle(tab)} onClick={() => handleTabSelect(tab)}>
            {TAB_LABELS[tab]}
          </div>
        ))}
      </div>

      {activeTab === "Today" && (
        <div style={sectionWrapperStyle}>
          <Today key={tabRenderKeys.Today} onNotify={showNotification} />
        </div>
      )}

      {activeTab === "Activities" && (
        <div style={sectionWrapperStyle}>
          <ActivityForm key={`activities-form-${tabRenderKeys.Activities}`} onNotify={showNotification} />
          {selectedActivity && (
            <ActivityDetail
              key={`activities-detail-${tabRenderKeys.Activities}-${selectedActivity.id}`}
              activity={selectedActivity}
              onClose={() => dispatch(selectActivity(null))}
              onNotify={showNotification}
            />
          )}
          <ActivityTable
            key={`activities-table-${tabRenderKeys.Activities}`}
            onNotify={showNotification}
            onOpenDetail={(activity) => dispatch(selectActivity(activity?.id || null))}
          />
        </div>
      )}

      {activeTab === "Stats" && (
        <div style={sectionWrapperStyle}>
          <Stats key={tabRenderKeys.Stats} onNotify={showNotification} />
        </div>
      )}

      {activeTab === "Entries" && (
        <div style={sectionWrapperStyle}>
          <EntryForm key={`entries-form-${tabRenderKeys.Entries}`} onNotify={showNotification} />
          <EntryTable key={`entries-table-${tabRenderKeys.Entries}`} onNotify={showNotification} />
        </div>
      )}

      {activeTab === "Admin" && (
        <div style={sectionWrapperStyle}>
          <Admin key={tabRenderKeys.Admin} onNotify={showNotification} />
        </div>
      )}
    </div>
  );
}
