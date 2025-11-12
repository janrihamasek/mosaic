import React, { useCallback, useEffect, useMemo } from "react";
import { useDispatch, useSelector } from "react-redux";
import { styles } from "../styles/common";
import {
  fetchWearableDay,
  fetchWearableTrends,
  resetWearableState,
  selectWearableDay,
  selectWearableError,
  selectWearableStatus,
} from "../store/wearableSlice";

const palette = {
  steps: "#38bdf8",
  heart: "#f97316",
  sleep: "#a78bfa",
};

const pageContainer = {
  ...styles.card,
  backgroundColor: "#111827",
  display: "flex",
  flexDirection: "column",
  gap: "1.25rem",
};

const headerRow = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  gap: "0.75rem",
  flexWrap: "wrap",
};

const headerTitle = {
  margin: 0,
  fontSize: "1.2rem",
};

const refreshButton = {
  ...styles.button,
  fontSize: "0.85rem",
};

const summaryGrid = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit,minmax(180px,1fr))",
  gap: "1rem",
};

const summaryCard = {
  ...styles.card,
  padding: "1rem",
  border: "1px solid rgba(255,255,255,0.05)",
  backgroundColor: "#1f2330",
};

const summaryLabel = {
  color: "#94a3b8",
  fontSize: "0.75rem",
  letterSpacing: "0.08em",
  textTransform: "uppercase",
};

const trendContainer = {
  display: "grid",
  gap: "1rem",
};

const trendCard = {
  ...styles.card,
  backgroundColor: "#1e1f29",
  padding: "1rem",
  border: "1px solid rgba(255,255,255,0.1)",
};

const barStrip = {
  display: "flex",
  gap: "0.35rem",
  alignItems: "flex-end",
  minHeight: "3rem",
};

const barBase = {
  flex: 1,
  height: "0.45rem",
  borderRadius: "999px",
  backgroundColor: "#0e1521",
};

const smallLabel = {
  fontSize: "0.75rem",
  color: "#94a3b8",
};

const trendSectionLabel = {
  ...smallLabel,
  marginTop: "0.35rem",
};

const formatNumber = (value) => {
  if (value == null || Number.isNaN(Number(value))) {
    return "—";
  }
  return Number(value).toLocaleString();
};

const renderBars = (entries = [], color) => {
  if (!entries.length) {
    return <p style={{ margin: 0, color: "#94a3b8" }}>No data yet.</p>;
  }
  const values = entries.map((entry) => Number(entry?.value ?? 0));
  const maxValue = Math.max(...values, 1);
  return (
    <div style={barStrip}>
      {entries.map((entry, index) => {
        const value = Number(entry?.value ?? 0);
        const width = `${(value / maxValue) * 100}%`;
        return (
          <div
            key={`${entry?.date || index}-${index}`}
            style={{
              ...barBase,
              width,
              backgroundColor: color,
            }}
            title={`${entry?.date || "Day"}: ${formatNumber(value)}`}
          />
        );
      })}
    </div>
  );
};

const TrendWidget = ({ title, color, weekData = [], monthData = [] }) => (
  <div style={trendCard}>
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
      <h3 style={{ margin: 0, fontSize: "1rem" }}>{title}</h3>
      <span style={smallLabel}>Trend</span>
    </div>
    <div style={trendSectionLabel}>Last 7 days</div>
    {renderBars(weekData, color)}
    <div style={trendSectionLabel}>Last 30 days</div>
    {renderBars(monthData, color)}
  </div>
);

export default function Wearables() {
  const dispatch = useDispatch();
  const day = useSelector(selectWearableDay);
  const status = useSelector(selectWearableStatus);
  const error = useSelector(selectWearableError);
  const trends = useSelector((state) => state.wearable.trends);

  const loadTrends = useCallback(() => {
    const metrics = ["steps", "sleep", "hr"];
    const windows = [7, 30];
    metrics.forEach((metric) => {
      windows.forEach((window) => {
        dispatch(fetchWearableTrends({ metric, window }));
      });
    });
  }, [dispatch]);

  useEffect(() => {
    dispatch(fetchWearableDay());
    loadTrends();
    return () => {
      dispatch(resetWearableState());
    };
  }, [dispatch, loadTrends]);

  const summaryMetrics = useMemo(() => {
    const sleepTotal = day?.sleep?.total_min ?? null;
    return [
      {
        key: "steps",
        label: "Steps",
        value: day?.steps ?? null,
        suffix: "steps",
        helper: day?.sleep?.sessions ? `${day.sleep.sessions} sleep session(s)` : null,
        color: palette.steps,
      },
      {
        key: "hr",
        label: "Resting HR",
        value: day?.hr?.rest ?? null,
        suffix: "bpm",
        helper: day?.hr?.avg ? `Avg ${Math.round(day.hr.avg)} bpm` : null,
        color: palette.heart,
      },
      {
        key: "sleep",
        label: "Sleep",
        value: sleepTotal,
        suffix: "min",
        helper: day?.sleep?.efficiency ? `Efficiency ${day.sleep.efficiency}%` : null,
        color: palette.sleep,
      },
    ];
  }, [day]);

  const handleRefresh = () => {
    dispatch(fetchWearableDay());
    loadTrends();
  };

  const trendData = (metric, window) => {
    const key = `${metric}:${window}`;
    return trends[key]?.values ?? [];
  };

  const loading = status === "loading";

  return (
    <div style={pageContainer}>
      <div style={headerRow}>
        <div>
          <h2 style={headerTitle}>Wearable Insights</h2>
          <p style={{ margin: 0, color: "#9ba3af" }}>Aggregated Health Connect data for today and trends.</p>
        </div>
        <button type="button" style={refreshButton} onClick={handleRefresh} disabled={loading}>
          {loading ? "Refreshing…" : "Refresh"}
        </button>
      </div>
      <div style={summaryGrid}>
        {summaryMetrics.map((metric) => (
          <div key={metric.key} style={summaryCard}>
            <span style={summaryLabel}>{metric.label}</span>
            <div style={{ fontSize: "1.85rem", fontWeight: 600, color: metric.color }}>
              {metric.value != null ? formatNumber(metric.value) : "—"}{" "}
              <span style={{ fontSize: "0.9rem", fontWeight: 400, color: "#94a3b8" }}>{metric.suffix}</span>
            </div>
            {metric.helper && <p style={{ margin: 0, color: "#94a3b8" }}>{metric.helper}</p>}
          </div>
        ))}
      </div>
      <div style={trendContainer}>
        {error && (
          <div style={{ ...summaryCard, backgroundColor: "#7f1d1d" }}>
            <p style={{ margin: 0 }}>Unable to load wearable metrics. Please try again.</p>
          </div>
        )}
        <TrendWidget
          title="Steps"
          color={palette.steps}
          weekData={trendData("steps", 7)}
          monthData={trendData("steps", 30)}
        />
        <TrendWidget
          title="Heart Rate"
          color={palette.heart}
          weekData={trendData("hr", 7)}
          monthData={trendData("hr", 30)}
        />
        <TrendWidget
          title="Sleep"
          color={palette.sleep}
          weekData={trendData("sleep", 7)}
          monthData={trendData("sleep", 30)}
        />
        {loading && (
          <div style={summaryCard}>
            <p style={{ margin: 0 }}>Loading wearable insights…</p>
          </div>
        )}
      </div>
    </div>
  );
}
