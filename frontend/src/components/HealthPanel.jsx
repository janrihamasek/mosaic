import React, { useCallback, useEffect, useMemo } from "react";
import { useDispatch, useSelector } from "react-redux";

import { styles } from "../styles/common";
import Loading from "./Loading";
import ErrorState from "./ErrorState";
import {
  loadHealth,
  loadMetrics,
  selectHealthState,
  selectMetricsState,
} from "../store/adminSlice";

const REFRESH_INTERVAL_MS = 60000;

function formatUptime(seconds) {
  if (!Number.isFinite(seconds)) return "—";
  const totalSeconds = Math.max(0, Math.floor(seconds));
  const days = Math.floor(totalSeconds / 86400);
  const hours = Math.floor((totalSeconds % 86400) / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  if (days > 0) {
    return `${days}d ${hours}h`;
  }
  if (hours > 0) {
    return `${hours}h ${minutes}m`;
  }
  return `${minutes}m`;
}

function formatNumber(value, digits = 2) {
  if (!Number.isFinite(value)) return "—";
  return value.toFixed(digits);
}

function deriveTone({ ok, warnThreshold = 0, value = 0 }) {
  if (typeof ok === "boolean") {
    return ok ? "ok" : "alert";
  }
  if (value > warnThreshold * 2) return "alert";
  if (value > warnThreshold) return "warn";
  return "info";
}

export default function HealthPanel() {
  const dispatch = useDispatch();
  const healthState = useSelector(selectHealthState);
  const metricsState = useSelector(selectMetricsState);

  const handleRefresh = useCallback(() => {
    dispatch(loadHealth());
    dispatch(loadMetrics());
  }, [dispatch]);

  useEffect(() => {
    if (healthState.status === "idle") {
      dispatch(loadHealth());
    }
    if (metricsState.status === "idle") {
      dispatch(loadMetrics());
    }
  }, [dispatch, healthState.status, metricsState.status]);

  useEffect(() => {
    const interval = setInterval(() => {
      handleRefresh();
    }, REFRESH_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [handleRefresh]);

  const initialLoading =
    (healthState.status === "loading" && !healthState.data) ||
    (metricsState.status === "loading" && !metricsState.data);

  const combinedError = healthState.error || metricsState.error;
  const hasData = Boolean(healthState.data && metricsState.data);

  const summaryCards = useMemo(() => {
    if (!healthState.data) return [];
    const { uptime_s, req_per_min, error_rate, db_ok, cache_ok } = healthState.data;
    return [
      {
        key: "uptime",
        label: "Uptime",
        value: formatUptime(uptime_s),
        tone: "info",
      },
      {
        key: "req_per_min",
        label: "Requests / min",
        value: formatNumber(req_per_min ?? Number.NaN),
        tone: "info",
      },
      {
        key: "error_rate",
        label: "Error rate",
        value: Number.isFinite(error_rate) ? `${formatNumber(error_rate * 100, 2)}%` : "0%",
        tone: deriveTone({ value: error_rate ?? 0, warnThreshold: 0.02 }),
      },
      {
        key: "db_ok",
        label: "Database",
        value: db_ok ? "Healthy" : "Check",
        tone: deriveTone({ ok: db_ok }),
      },
      {
        key: "cache_ok",
        label: "Cache",
        value: cache_ok ? "Healthy" : "Check",
        tone: deriveTone({ ok: cache_ok }),
      },
    ];
  }, [healthState.data]);

  const metricsRows = useMemo(() => {
    const endpoints = metricsState.data?.endpoints ?? [];
    return [...endpoints].sort((a, b) => (b.count || 0) - (a.count || 0));
  }, [metricsState.data]);

  const lastUpdatedText = useMemo(() => {
    const timestamps = [healthState.lastFetched, metricsState.lastFetched].filter(Boolean);
    if (!timestamps.length) return "Never";
    const latest = new Date(Math.max(...timestamps));
    return latest.toLocaleTimeString();
  }, [healthState.lastFetched, metricsState.lastFetched]);

  const lastMetricsUpdate = useMemo(() => {
    const iso = metricsState.data?.last_updated;
    if (!iso) return null;
    try {
      return new Date(iso).toLocaleString();
    } catch (_err) {
      return iso;
    }
  }, [metricsState.data]);

  const summaryGridStyle = useMemo(
    () => ({
      display: "grid",
      gridTemplateColumns: "repeat(auto-fit, minmax(170px, 1fr))",
      gap: "0.85rem",
    }),
    []
  );

  const summaryCardToneStyles = {
    ok: { borderColor: "#2f9e44", backgroundColor: "#1f3424" },
    info: { borderColor: "#2f7edb", backgroundColor: "#1f2836" },
    warn: { borderColor: "#f6c343", backgroundColor: "#3b2f1a" },
    alert: { borderColor: "#f44336", backgroundColor: "#3b1f1f" },
  };

  if (initialLoading) {
    return <Loading message="Loading health metrics…" />;
  }

  if (combinedError && !hasData) {
    return <ErrorState message={combinedError} onRetry={handleRefresh} />;
  }

  return (
    <div
      style={{
        ...styles.card,
        display: "flex",
        flexDirection: "column",
        gap: "1rem",
      }}
    >
      <div
        style={{
          display: "flex",
          flexDirection: "row",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "0.75rem",
        }}
      >
        <div>
          <h3 style={{ margin: 0 }}>System Health</h3>
          <p style={{ margin: "0.2rem 0 0", color: "#9ca3af", fontSize: "0.9rem" }}>
            Last refresh: {lastUpdatedText} • Auto-refresh every 60s
          </p>
        </div>
        <button
          type="button"
          onClick={handleRefresh}
          style={{
            ...styles.button,
            minWidth: "7rem",
            opacity: healthState.status === "loading" || metricsState.status === "loading" ? 0.85 : 1,
          }}
        >
          Refresh
        </button>
      </div>

      {combinedError && hasData && (
        <ErrorState message={combinedError} onRetry={handleRefresh} actionLabel="Retry now" />
      )}

      {summaryCards.length > 0 ? (
        <div style={summaryGridStyle}>
          {summaryCards.map((card) => (
            <div
              key={card.key}
              style={{
                border: "1px solid #2f3034",
                borderRadius: "0.5rem",
                padding: "0.85rem",
                display: "flex",
                flexDirection: "column",
                gap: "0.35rem",
                ...(summaryCardToneStyles[card.tone] ?? {}),
              }}
            >
              <span style={{ fontSize: "0.85rem", color: "#c1c6cf" }}>{card.label}</span>
              <strong style={{ fontSize: "1.4rem" }}>{card.value}</strong>
            </div>
          ))}
        </div>
      ) : (
        <p style={{ color: "#c1c6cf" }}>Health data will appear after the first refresh.</p>
      )}

      <div>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
          <h4 style={{ margin: 0 }}>Endpoints</h4>
          <small style={{ color: "#9ca3af" }}>
            Metrics updated: {lastMetricsUpdate ?? "No samples yet"}
          </small>
        </div>
        {metricsRows.length === 0 ? (
          <p style={{ color: "#c1c6cf" }}>No request metrics recorded yet.</p>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table
              style={{
                width: "100%",
                borderCollapse: "collapse",
                marginTop: "0.75rem",
                minWidth: "32rem",
              }}
            >
              <thead>
                <tr style={{ textAlign: "left", color: "#9ca3af" }}>
                  <th style={{ padding: "0.5rem" }}>Endpoint</th>
                  <th style={{ padding: "0.5rem" }}>Method</th>
                  <th style={{ padding: "0.5rem" }}>Count</th>
                  <th style={{ padding: "0.5rem" }}>Avg latency (ms)</th>
                  <th style={{ padding: "0.5rem" }}>4xx</th>
                  <th style={{ padding: "0.5rem" }}>5xx</th>
                </tr>
              </thead>
              <tbody>
                {metricsRows.map((row) => (
                  <tr
                    key={`${row.endpoint}-${row.method}`}
                    style={{ borderTop: "1px solid #2f3034" }}
                  >
                    <td style={{ padding: "0.5rem" }}>{row.endpoint}</td>
                    <td style={{ padding: "0.5rem" }}>{row.method}</td>
                    <td style={{ padding: "0.5rem" }}>{row.count ?? 0}</td>
                    <td style={{ padding: "0.5rem" }}>
                      {formatNumber(row.avg_latency_ms ?? Number.NaN)}
                    </td>
                    <td style={{ padding: "0.5rem" }}>{row.errors_4xx ?? 0}</td>
                    <td style={{ padding: "0.5rem" }}>{row.errors_5xx ?? 0}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
