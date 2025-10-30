import React, { useMemo, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { styles } from "../styles/common";
import { formatError } from "../utils/errors";
import { loadStats, selectStatsState } from "../store/entriesSlice";
import { useCompactLayout } from "../utils/useBreakpoints";

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
  const dispatch = useDispatch();
  const { data, status, options, range } = useSelector(selectStatsState);
  const [metric, setMetric] = useState("progress");
  const loading = status === "loading";
  const { isCompact } = useCompactLayout();
  const filterRowStyle = {
    display: "grid",
    gridTemplateColumns: isCompact ? "1fr" : "repeat(auto-fit, minmax(10rem, 1fr))",
    gap: "0.75rem",
    marginBottom: "1rem",
  };
  const filterSelectStyle = {
    ...styles.input,
    width: "100%",
  };

  const handleLoad = async (nextOptions) => {
    try {
      await dispatch(loadStats(nextOptions)).unwrap();
    } catch (err) {
      onNotify?.(`Failed to load stats: ${formatError(err)}`, "error");
    }
  };

  const processed = useMemo(() => {
    return data
      .map((item) => {
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
      })
      .sort((a, b) => b.ratio - a.ratio);
  }, [data]);

  const renderRow = (item) => {
    const ratioLabel =
      item.totalGoal > 0 ? `${item.totalValue.toFixed(1)} / ${item.totalGoal.toFixed(1)}` : "N/A";
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
              backgroundColor: item.ratio >= 0.5 ? styles.highlightRow.backgroundColor : "#8b1e3f",
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
      <div style={filterRowStyle}>
        <select
          value={metric}
          onChange={(e) => setMetric(e.target.value)}
          style={filterSelectStyle}
        >
          {metricOptions.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
        <select
          value={options.group}
          onChange={(e) => handleLoad({ group: e.target.value })}
          style={filterSelectStyle}
        >
          {groupOptions.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
        <select
          value={options.period}
          onChange={(e) => handleLoad({ period: Number(e.target.value) })}
          style={filterSelectStyle}
        >
          {periodOptions.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </div>
      {range.start && range.end && (
        <div style={{ alignSelf: "flex-start", fontSize: "0.8125rem", color: "#9ba3af" }}>
          {range.start} → {range.end}
        </div>
      )}

      {loading && <div style={styles.loadingText}>⏳ Loading stats...</div>}

      {!loading && processed.length === 0 && (
        <div style={{ color: "#9ba3af", fontStyle: "italic" }}>
          No data available for the selected filters.
        </div>
      )}

      {!loading && processed.length > 0 && <div>{processed.map(renderRow)}</div>}
    </div>
  );
}
