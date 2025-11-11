import React, { useEffect, useMemo } from "react";
import { useDispatch, useSelector } from "react-redux";

import { styles } from "../styles/common";
import {
  loadWearableDay,
  loadWearableTrends,
  selectWearableDay,
  selectWearableStatus,
  selectWearableTrends,
} from "../store/wearableSlice";

const palette = {
  steps: "#38bdf8",
  heart: "#f97316",
  sleep: "#a78bfa",
};

const stripStyles = {
  display: "flex",
  gap: "0.25rem",
  marginTop: "0.8rem",
  alignItems: "flex-end",
  minHeight: "3rem",
};

const barBase = {
  flex: 1,
  height: "0.4rem",
  borderRadius: "999px",
  backgroundColor: "#1e293b",
};

const summaryCard = {
  ...styles.card,
  padding: "1rem",
  border: "1px solid rgba(255,255,255,0.05)",
  display: "flex",
  flexDirection: "column",
  gap: "0.25rem",
};

const labelStyle = {
  color: "#94a3b8",
  fontSize: "0.75rem",
  letterSpacing: "0.08em",
  textTransform: "uppercase",
};

function buildSeries(entries = [], limit = 7) {
  if (!Array.isArray(entries) || entries.length === 0) {
    return [];
  }
  return entries.slice(-limit);
}

function renderBars(entries, color) {
  const values = entries.map((entry) => Number(entry?.value ?? entry?.amount ?? entry?.steps ?? 0));
  const maxValue = Math.max(...values, 1);
  return (
    <div style={stripStyles}>
      {entries.map((entry, index) => {
        const value = Number(entry?.value ?? entry?.amount ?? entry?.steps ?? 0);
        const width = `${(value / maxValue) * 100}%`;
        return (
          <div
            key={`${entry?.day || entry?.date || index}-${index}`}
            style={{
              ...barBase,
              width,
              backgroundColor: color,
            }}
            title={`${entry?.day || entry?.date || "Day"}: ${value}`}
          />
        );
      })}
    </div>
  );
}

function TrendWidget({ title, color, data = [] }) {
  const seven = buildSeries(data, 7);
  const thirty = buildSeries(data, 30);
  return (
    <div style={{ ...summaryCard, backgroundColor: "#111827" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h3 style={{ margin: 0, fontSize: "1rem" }}>{title}</h3>
        <span style={{ color: "#94a3b8", fontSize: "0.75rem" }}>Trend</span>
      </div>
      <div style={{ fontSize: "0.75rem", color: "#cbd5f5" }}>Last 7 days</div>
      {seven.length ? renderBars(seven, color) : <p style={{ margin: 0 }}>No data for 7 days.</p>}
      <div style={{ fontSize: "0.75rem", color: "#cbd5f5" }}>Last 30 days</div>
      {thirty.length ? renderBars(thirty, color) : <p style={{ margin: 0 }}>No data for 30 days.</p>}
    </div>
  );
}

export default function Wearables() {
  const dispatch = useDispatch();
  const day = useSelector(selectWearableDay);
  const trends = useSelector(selectWearableTrends);
  const status = useSelector(selectWearableStatus);

  useEffect(() => {
    dispatch(loadWearableDay());
    dispatch(loadWearableTrends());
  }, [dispatch]);

  const summaryMetrics = useMemo(() => {
    const sleepMinutes = day?.sleep_seconds != null ? Math.round(day.sleep_seconds / 60) : null;
    return [
      {
        key: "steps",
        label: "Steps",
        value: day?.steps,
        suffix: "steps",
        helper: day?.distance_meters ? `${Math.round(day.distance_meters)} m` : null,
        color: palette.steps,
      },
      {
        key: "hr",
        label: "Resting HR",
        value: day?.resting_heart_rate,
        suffix: "bpm",
        helper: day?.hrv_rmssd_ms ? `HRV ${Math.round(day.hrv_rmssd_ms)} ms` : null,
        color: palette.heart,
      },
      {
        key: "sleep",
        label: "Sleep",
        value: sleepMinutes,
        suffix: "min",
        helper: day?.sleep_seconds ? "tracked" : null,
        color: palette.sleep,
      },
    ];
  }, [day]);

  const loading = status === "loading";
  const error = status === "failed";

  return (
    <div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(180px,1fr))", gap: "1rem" }}>
        {summaryMetrics.map((metric) => (
          <div key={metric.key} style={summaryCard}>
            <span style={labelStyle}>{metric.label}</span>
            <div style={{ fontSize: "1.85rem", fontWeight: 600, color: metric.color }}>
              {metric.value != null ? metric.value : "—"}{" "}
              <span style={{ fontSize: "0.9rem", fontWeight: 400, color: "#94a3b8" }}>{metric.suffix}</span>
            </div>
            {metric.helper && <p style={{ margin: 0, color: "#94a3b8" }}>{metric.helper}</p>}
          </div>
        ))}
      </div>
      <div style={{ marginTop: "1.5rem", display: "grid", gap: "1rem" }}>
        {error && (
          <div style={{ ...summaryCard, backgroundColor: "#7f1d1d" }}>
            <p style={{ margin: 0 }}>Unable to load wearable metrics. Please try again.</p>
          </div>
        )}
        {!error && (
          <>
            <TrendWidget title="Steps" color={palette.steps} data={trends?.steps || trends?.steps7 || []} />
            <TrendWidget title="Heart Rate" color={palette.heart} data={trends?.heart_rate || trends?.hr || []} />
            <TrendWidget title="Sleep" color={palette.sleep} data={trends?.sleep || trends?.sleep_minutes || []} />
          </>
        )}
        {loading && (
          <div style={summaryCard}>
            <p style={{ margin: 0 }}>Loading wearable insights…</p>
          </div>
        )}
      </div>
    </div>
  );
}
