import React, { useEffect, useMemo, useState } from "react";
import { fetchProgressStats } from "../api";
import { styles } from "../styles/common";

const metricOptions = [{ value: "progress", label: "Progress" }];
const groupOptions = [
  { value: "activity", label: "Activity" },
  { value: "category", label: "Category" },
];
const periodOptions = [
  { value: 30, label: "30 days" },
  { value: 90, label: "90 days" },
];

const progressBarStyle = {
  container: { height: 8, backgroundColor: "#333", borderRadius: 4, overflow: "hidden" },
  fill: {
    backgroundColor: "#3a7bd5",
    height: "100%",
    transition: "width 0.3s ease",
  },
};

export default function Stats({ onNotify }) {
  const [metric, setMetric] = useState("progress");
  const [group, setGroup] = useState("activity");
  const [period, setPeriod] = useState(30);
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState([]);
  const [range, setRange] = useState({ start: null, end: null });

  useEffect(() => {
    if (metric !== "progress") return;
    let isMounted = true;

    const load = async () => {
      setLoading(true);
      try {
        const payload = await fetchProgressStats({ group, period });
        if (!isMounted) return;
        setData(payload?.data || []);
        setRange({ start: payload?.start_date, end: payload?.end_date });
      } catch (err) {
        if (isMounted) {
          setData([]);
          onNotify?.(`Failed to load stats: ${err.message}`, "error");
        }
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    };

    load();
    return () => {
      isMounted = false;
    };
  }, [metric, group, period, onNotify]);

  const processed = useMemo(() => {
    return data.map((item) => {
      const totalGoal = Number(item.total_goal) || 0;
      const totalValue = Number(item.total_value) || 0;
      const ratio = totalGoal > 0 ? totalValue / totalGoal : 0;
      return {
        ...item,
        totalGoal,
        totalValue,
        ratio,
        percent: totalGoal > 0 ? Math.min(ratio * 100, 100) : 0,
      };
    }).sort((a, b) => b.ratio - a.ratio);
  }, [data]);

  const renderRow = (item) => {
    const ratioLabel = item.totalGoal > 0 ? `${item.totalValue.toFixed(1)} / ${item.totalGoal.toFixed(1)}` : "N/A";
    const percentLabel = item.totalGoal > 0 ? `${Math.round(item.ratio * 100)}%` : "N/A";

    return (
      <div
        key={item.name}
        style={{
          padding: "12px 0",
          borderBottom: "1px solid #333",
          display: "flex",
          flexDirection: "column",
          gap: 6,
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <span style={{ fontWeight: 600 }}>{item.name}</span>
          <span style={{ fontSize: 12, color: "#9ba3af" }}>
            {percentLabel}
            {item.totalGoal > 0 && ` (${ratioLabel})`}
          </span>
        </div>
        <div style={progressBarStyle.container}>
          <div
            style={{
              ...progressBarStyle.fill,
              width: `${item.percent}%`,
              backgroundColor: item.ratio >= 0.5 ? styles.highlightRow.backgroundColor : '#8b1e3f',
            }}
            role="progressbar"
            aria-label={`Progress for ${item.name}`}
            aria-valuemin={0}
            aria-valuemax={item.totalGoal > 0 ? item.totalGoal : undefined}
            aria-valuenow={item.totalGoal > 0 ? Math.min(item.totalValue, item.totalGoal) : undefined}
          />
        </div>
      </div>
    );
  };

  return (
    <div style={styles.card}>
      <div style={{ display: "flex", gap: 12, flexWrap: "wrap", marginBottom: 16 }}>
        <select
          value={metric}
          onChange={(e) => setMetric(e.target.value)}
          style={{ ...styles.input, width: 140 }}
        >
          {metricOptions.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
        <select
          value={group}
          onChange={(e) => setGroup(e.target.value)}
          style={{ ...styles.input, width: 140 }}
        >
          {groupOptions.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
        <select
          value={period}
          onChange={(e) => setPeriod(Number(e.target.value))}
          style={{ ...styles.input, width: 140 }}
        >
          {periodOptions.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
        {range.start && range.end && (
          <div style={{ alignSelf: "center", fontSize: 12, color: "#9ba3af" }}>
            {range.start} → {range.end}
          </div>
        )}
      </div>

      {loading && <div style={styles.loadingText}>⏳ Loading stats...</div>}

      {!loading && processed.length === 0 && (
        <div style={{ color: "#9ba3af", fontStyle: "italic" }}>No data available for the selected filters.</div>
      )}

      {!loading && processed.length > 0 && (
        <div>
          {processed.map(renderRow)}
        </div>
      )}
    </div>
  );
}
