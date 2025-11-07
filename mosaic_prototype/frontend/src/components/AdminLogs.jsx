import React, { useCallback, useEffect, useMemo, useState } from "react";
import { useDispatch, useSelector } from "react-redux";

import { styles } from "../styles/common";
import DataTable from "./shared/DataTable";
import ErrorState from "./ErrorState";
import {
  loadActivityLogs,
  loadRuntimeLogs,
  selectActivityLogsState,
  selectRuntimeLogsState,
} from "../store/adminSlice";

const REFRESH_INTERVAL_MS = 60000;
const TABS = [
  { id: "activity", label: "Activity Logs" },
  { id: "runtime", label: "Runtime Logs" },
];
const LOCAL_TIMEZONE = Intl.DateTimeFormat().resolvedOptions().timeZone;

function formatTimestamp(value) {
  if (!value) return "—";
  try {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
      return value;
    }
    const pad = (num) => String(num).padStart(2, "0");
    const year = date.getFullYear();
    const month = pad(date.getMonth() + 1);
    const day = pad(date.getDate());
    const hours = pad(date.getHours());
    const minutes = pad(date.getMinutes());
    const seconds = pad(date.getSeconds());
    return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`;
  } catch (_err) {
    return value;
  }
}

function formatUser(row) {
  const username =
    row?.context?.username ??
    row?.username ??
    row?.runtime?.username ??
    row?.runtime?.user ??
    row?.runtime?.context?.username;
  const userId =
    row?.user_id ??
    row?.runtime?.user_id ??
    row?.runtime?.context?.user_id;
  if (username) {
    return username;
  }
  if (userId != null) {
    return `User #${userId}`;
  }
  return "System";
}

function toLevelBadge(level) {
  const normalized = (level || "info").toLowerCase();
  const palette = {
    error: { bg: "#3b1f24", color: "#f87171" },
    warning: { bg: "#3b2f1a", color: "#facc15" },
    warn: { bg: "#3b2f1a", color: "#facc15" },
    info: { bg: "#1f2c3b", color: "#60a5fa" },
    debug: { bg: "#1f2c3b", color: "#93c5fd" },
    success: { bg: "#1f3424", color: "#86efac" },
  };
  const tone = palette[normalized] || palette.info;
  return (
    <span
      style={{
        padding: "0.15rem 0.5rem",
        borderRadius: "999px",
        fontSize: "0.75rem",
        fontWeight: 600,
        letterSpacing: "0.02em",
        textTransform: "uppercase",
        backgroundColor: tone.bg,
        color: tone.color,
      }}
    >
      {normalized}
    </span>
  );
}

function formatLastUpdated(timestamp) {
  if (!timestamp) return "Never";
  try {
    return new Date(timestamp).toLocaleTimeString();
  } catch (_err) {
    return timestamp;
  }
}

function parseRuntimePayload(message) {
  if (!message) {
    return {};
  }
  if (typeof message === "object") {
    return message;
  }
  if (typeof message === "string") {
    try {
      return JSON.parse(message);
    } catch (_err) {
      return {};
    }
  }
  return {};
}

const formatDurationMs = (value) => {
  if (!Number.isFinite(value)) {
    return "—";
  }
  return `${Math.round(value)} ms`;
};

export default function AdminLogs() {
  const dispatch = useDispatch();
  const [activeTab, setActiveTab] = useState(TABS[0].id);
  const activityState = useSelector(selectActivityLogsState);
  const runtimeState = useSelector(selectRuntimeLogsState);

  const handleRefreshAll = useCallback(() => {
    dispatch(loadActivityLogs());
    dispatch(loadRuntimeLogs());
  }, [dispatch]);

  useEffect(() => {
    if (activityState.status === "idle") {
      dispatch(loadActivityLogs());
    }
    if (runtimeState.status === "idle") {
      dispatch(loadRuntimeLogs());
    }
  }, [dispatch, activityState.status, runtimeState.status]);

  useEffect(() => {
    const interval = setInterval(() => {
      handleRefreshAll();
    }, REFRESH_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [handleRefreshAll]);

  const activityRows = useMemo(() => activityState.data?.items ?? [], [activityState.data]);
  const runtimeRows = useMemo(
    () =>
      (runtimeState.data?.logs ?? []).map((log, index) => ({
        id: log.id ?? `${log.timestamp ?? "log"}-${index}`,
        ...log,
        runtime: parseRuntimePayload(log.message),
      })),
    [runtimeState.data]
  );

  const activityColumns = useMemo(
    () => [
      {
        key: "timestamp",
        label: "Timestamp",
        render: (row) => formatTimestamp(row.timestamp),
      },
      {
        key: "user",
        label: "User",
        render: (row) => formatUser(row),
      },
      {
        key: "event_type",
        label: "Event Type",
        render: (row) => row.event_type || "—",
      },
      {
        key: "level",
        label: "Level",
        width: "6rem",
        render: (row) => toLevelBadge(row.level),
      },
      {
        key: "message",
        label: "Message",
        width: "40%",
        render: (row) => row.message || "—",
      },
    ],
    []
  );

  const runtimeColumns = useMemo(() => {
    const renderRequest = (row) => {
      const method =
        row.runtime?.method ??
        row.runtime?.http_method ??
        row.method ??
        row.http_method;
      const route =
        row.runtime?.route ??
        row.runtime?.path ??
        row.route ??
        row.endpoint ??
        row.runtime?.endpoint;
      if (!route && !method) {
        return "—";
      }
      return `${(method || "GET").toUpperCase()} ${route || "/"}`;
    };
    const renderStatus = (row) => {
      const status =
        row.runtime?.status_code ??
        row.runtime?.status ??
        row.status_code ??
        row.status;
      return status != null ? status : "—";
    };
    const renderDuration = (row) => {
      const duration =
        row.runtime?.duration_ms ??
        row.runtime?.duration ??
        row.duration_ms ??
        row.duration;
      return formatDurationMs(duration);
    };
    return [
      {
        key: "timestamp",
        label: "Timestamp",
        render: (row) => formatTimestamp(row.timestamp),
      },
      {
        key: "user",
        label: "User",
        render: (row) => formatUser(row),
      },
      {
        key: "request",
        label: "Request",
        width: "30%",
        render: renderRequest,
      },
      {
        key: "status",
        label: "Status",
        render: renderStatus,
      },
      {
        key: "duration",
        label: "Duration",
        render: renderDuration,
      },
      {
        key: "level",
        label: "Level",
        width: "6rem",
        render: (row) => toLevelBadge(row.level),
      },
    ];
  }, []);

  const activeConfig = useMemo(() => {
    if (activeTab === "runtime") {
      return {
        title: "Runtime Logs",
        description: "Recent in-memory log buffer (non-persistent).",
        state: runtimeState,
        rows: runtimeRows,
        columns: runtimeColumns,
        emptyMessage: "No runtime logs captured yet.",
        loadingMessage: "Loading runtime logs…",
      };
    }
    return {
      title: "Activity Logs",
      description: "Persistent audit trail for user and system events.",
      state: activityState,
      rows: activityRows,
      columns: activityColumns,
      emptyMessage: "No activity logs recorded yet.",
      loadingMessage: "Loading activity logs…",
    };
  }, [
    activeTab,
    activityColumns,
    activityRows,
    activityState,
    runtimeColumns,
    runtimeRows,
    runtimeState,
  ]);

  const isInitialLoading = activeConfig.state.status === "loading" && !activeConfig.state.data;
  const isRefreshing = activeConfig.state.status === "loading" && Boolean(activeConfig.state.data);
  const hasRows = activeConfig.rows.length > 0;
  const activeError = activeConfig.state.error;
  const refreshButtonDisabled = activityState.status === "loading" || runtimeState.status === "loading";
  const tabSpecificSubtitle =
    activeTab === "runtime"
      ? "Recent in-memory request traces (non-persistent)."
      : "Persistent user & system events stored in the database.";

  return (
    <div
      style={{
        ...styles.card,
        display: "flex",
        flexDirection: "column",
        gap: "1.25rem",
      }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
          flexWrap: "wrap",
          gap: "0.75rem",
        }}
      >
        <div>
          <h3 style={{ margin: 0 }}>System Logs</h3>
          <p style={{ margin: "0.25rem 0 0", color: "#9ca3af", fontSize: "0.9rem" }}>
            {tabSpecificSubtitle}
          </p>
          <p style={{ margin: "0.15rem 0 0", color: "#9ca3af", fontSize: "0.85rem" }}>
            Auto-refresh every 60s • Last update: {formatLastUpdated(activeConfig.state.lastFetched)}
            {isRefreshing ? " (refreshing…)" : ""} • Times shown in {LOCAL_TIMEZONE}
          </p>
        </div>
        <button
          type="button"
          onClick={handleRefreshAll}
          disabled={refreshButtonDisabled}
          style={{
            ...styles.button,
            minWidth: "7rem",
            opacity: refreshButtonDisabled ? 0.85 : 1,
          }}
        >
          Refresh now
        </button>
      </div>

      <div
        role="tablist"
        aria-label="Log categories"
        style={{
          display: "flex",
          gap: "0.5rem",
          flexWrap: "wrap",
        }}
      >
        {TABS.map((tab) => (
          <button
            key={tab.id}
            type="button"
            role="tab"
            aria-selected={activeTab === tab.id}
            onClick={() => setActiveTab(tab.id)}
            style={{
              ...styles.tab,
              flex: "0 0 auto",
              borderRadius: "0.5rem",
              padding: "0.5rem 1rem",
              backgroundColor: activeTab === tab.id ? "#2b2c30" : "transparent",
              borderColor: activeTab === tab.id ? "#3a7bd5" : "transparent",
              color: activeTab === tab.id ? "#fff" : "#cbd5f5",
              fontWeight: activeTab === tab.id ? 600 : 500,
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div>
        <p style={{ margin: "0 0 0.85rem", color: "#c1c6cf" }}>
          {activeConfig.description}
        </p>
        {activeError && hasRows && (
          <ErrorState
            message={activeError}
            onRetry={handleRefreshAll}
            actionLabel="Retry fetch"
          />
        )}
        <DataTable
          columns={activeConfig.columns}
          data={activeConfig.rows}
          isLoading={isInitialLoading}
          error={!hasRows ? activeError : null}
          emptyMessage={activeConfig.emptyMessage}
          loadingMessage={activeConfig.loadingMessage}
        />
      </div>
    </div>
  );
}
