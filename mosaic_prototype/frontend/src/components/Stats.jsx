import React, { useEffect, useMemo, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { Loading } from "./Loading";
import { ErrorState } from "./ErrorState";
import { styles } from "../styles/common";
import { formatError } from "../utils/errors";
import { loadStats, selectStatsState } from "../store/entriesSlice";
import { useCompactLayout } from "../utils/useBreakpoints";

const pieColors = ["#3a7bd5", "#f1b24a", "#8b1e3f", "#43cea2", "#8f36ff", "#9ba3af"];

const containerStyle = {
  ...styles.card,
  display: "flex",
  flexDirection: "column",
  gap: "1.5rem",
};

const headerStyle = {
  display: "flex",
  justifyContent: "space-between",
  gap: "1rem",
  flexWrap: "wrap",
};

const sectionGridBase = {
  display: "grid",
  gap: "1.5rem",
};

const meterContainer = {
  backgroundColor: "#2f3034",
  borderRadius: "999px",
  overflow: "hidden",
  height: "0.75rem",
};

const meterFillBase = {
  height: "100%",
  transition: "width 220ms ease-in-out",
  borderRadius: "999px",
};

const dualBarContainer = {
  ...meterContainer,
  display: "flex",
};

const toNumber = (value, fallback = 0) => {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
};

const formatPercent = (value) => `${toNumber(value).toFixed(1)}%`;
const normaliseIndex = (index, length) => {
  if (!length) return 0;
  const mod = index % length;
  return mod >= 0 ? mod : mod + length;
};

const navButtonStyle = {
  backgroundColor: "#1f2024",
  border: "1px solid #38393e",
  color: "#e6e6e6",
  borderRadius: "0.4rem",
  padding: "0.35rem 0.7rem",
  cursor: "pointer",
  transition: "opacity 160ms ease-in-out",
};

export default function Stats({ onNotify }) {
  const dispatch = useDispatch();
  const { snapshot, status, error, date } = useSelector(selectStatsState);
  const { isCompact } = useCompactLayout();

  const refetchStats = async () => {
    try {
      await dispatch(loadStats({ date })).unwrap();
    } catch (err) {
      onNotify?.(`Failed to load stats: ${formatError(err)}`, "error");
    }
  };

  const distributionWithColors = useMemo(() => {
    if (!snapshot?.activity_distribution?.length) {
      return [];
    }
    return snapshot.activity_distribution.map((item, index) => ({
      ...item,
      color: pieColors[index % pieColors.length],
    }));
  }, [snapshot]);

  const pieBackground = useMemo(() => {
    if (!distributionWithColors.length) {
      return "#2f3034";
    }
    let currentAngle = 0;
    const segments = distributionWithColors.map((item, idx) => {
      const percent = Math.max(0, Math.min(100, toNumber(item.percent)));
      let sweep = (percent / 100) * 360;
      if (idx === distributionWithColors.length - 1) {
        sweep = Math.max(0, 360 - currentAngle);
      }
      const start = currentAngle;
      const end = Math.min(360, start + sweep);
      currentAngle = end;
      return `${item.color} ${start}deg ${end}deg`;
    });
    return `conic-gradient(${segments.join(", ")})`;
  }, [distributionWithColors]);

  const lineChart = useMemo(() => {
    const last7 = toNumber(snapshot?.avg_goal_fulfillment?.last_7_days);
    const last30 = toNumber(snapshot?.avg_goal_fulfillment?.last_30_days);
    const values = [last7, last30];
    const labels = ["7d", "30d"];
    const width = 200;
    const height = 110;
    const padding = 18;
    const drawableHeight = height - padding * 2;
    const step = values.length > 1 ? (width - padding * 2) / (values.length - 1) : 0;
    const points = values.map((value, index) => {
      const x = padding + index * step;
      const y = height - padding - (Math.min(100, Math.max(0, value)) / 100) * drawableHeight;
      return { x, y, label: labels[index], value };
    });
    const path = points.length > 1 ? points.map((p) => `${p.x},${p.y}`).join(" ") : "";
    return { points, path, width, height };
  }, [snapshot]);

  const goalCompletion = toNumber(snapshot?.goal_completion_today);
  const streakLength = toNumber(snapshot?.streak_length, 0);
  const activeRatio = snapshot?.active_days_ratio || {};
  const activeDays = toNumber(activeRatio.active_days, 0);
  const totalDays = toNumber(activeRatio.total_days, 0) || 30;
  const activePercent = toNumber(activeRatio.percent, 0);

  const polarity = snapshot?.positive_vs_negative || {};
  const positiveCount = toNumber(polarity.positive, 0);
  const negativeCount = toNumber(polarity.negative, 0);
  const polarityRatio = toNumber(polarity.ratio, 0);
  const totalPolarity = positiveCount + negativeCount;
  const positiveWidth = totalPolarity ? (positiveCount / totalPolarity) * 100 : 0;
  const negativeWidth = totalPolarity ? (negativeCount / totalPolarity) * 100 : 0;

  const avgByCategory = snapshot?.avg_goal_fulfillment_by_category || [];
  const [avgCategoryIndex, setAvgCategoryIndex] = useState(0);
  useEffect(() => {
    setAvgCategoryIndex(0);
  }, [avgByCategory.length]);
  const avgCategoryLength = avgByCategory.length;
  const activeAvgCategory =
    avgCategoryLength > 0 ? avgByCategory[normaliseIndex(avgCategoryIndex, avgCategoryLength)] : null;

  const consistencyByCategory = snapshot?.top_consistent_activities_by_category || [];
  const [consistencyIndex, setConsistencyIndex] = useState(0);
  useEffect(() => {
    setConsistencyIndex(0);
  }, [consistencyByCategory.length]);
  const consistencyLength = consistencyByCategory.length;
  const activeConsistencyBucket =
    consistencyLength > 0
      ? consistencyByCategory[normaliseIndex(consistencyIndex, consistencyLength)]
      : null;
  const canCycleConsistency = consistencyLength > 1;

  const sectionGridStyle = {
    ...sectionGridBase,
    gridTemplateColumns: isCompact ? "1fr" : "repeat(2, minmax(0, 1fr))",
  };

  if (status === "loading") {
    return (
      <div style={containerStyle}>
        <Loading message="Loading dashboard stats…" />
      </div>
    );
  }

  if (status === "failed") {
    return (
      <div style={containerStyle}>
        <ErrorState
          message={formatError(error, "Failed to load stats.")}
          onRetry={refetchStats}
          actionLabel="Retry"
        />
      </div>
    );
  }

  return (
    <div style={containerStyle}>
      <div style={headerStyle}>
        <div style={{ display: "flex", flexDirection: "column", gap: "0.35rem" }}>
          <h2 style={{ margin: 0, fontSize: "1.35rem" }}>Progress Overview</h2>
          <span style={{ color: "#9ba3af", fontSize: "0.95rem" }}>
            Unified snapshot for the past 30 days to power the dashboard.
          </span>
        </div>
        <button
          type="button"
          onClick={refetchStats}
          style={{ ...styles.button }}
        >
          Refresh
        </button>
      </div>

      {!snapshot && status === "succeeded" && (
        <div style={{ color: "#9ba3af", fontStyle: "italic" }}>
          No statistics available yet. Log a few activities to get insights.
        </div>
      )}

      {snapshot && (
        <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
          <div style={sectionGridStyle}>
            <div
              style={{
                display: "flex",
                flexDirection: "column",
                gap: "0.75rem",
                padding: "1rem",
                borderRadius: "0.5rem",
                backgroundColor: "#232428",
                border: "1px solid #303136",
              }}
            >
              <span style={{ color: "#9ba3af", fontSize: "0.9rem", textTransform: "uppercase" }}>
                Goal Completion Today
              </span>
              <div style={{ fontSize: "2.1rem", fontWeight: 600 }}>{formatPercent(goalCompletion)}</div>
              <div style={meterContainer} aria-hidden="true">
                <div
                  style={{
                    ...meterFillBase,
                    width: `${Math.min(goalCompletion, 100)}%`,
                    background:
                      goalCompletion >= 80 ? "linear-gradient(90deg,#3a7bd5,#43cea2)" : "#8b1e3f",
                  }}
                />
              </div>
              <span
                style={{
                  alignSelf: "flex-start",
                  backgroundColor: "#3a7bd533",
                  border: "1px solid #3a7bd5",
                  borderRadius: "999px",
                  padding: "0.25rem 0.75rem",
                  fontSize: "0.8rem",
                  fontWeight: 600,
                  color: "#c4d9ff",
                }}
              >
                Streak: {streakLength} day{streakLength === 1 ? "" : "s"}
              </span>
            </div>

            <div
              style={{
                display: "flex",
                flexDirection: "column",
                gap: "0.75rem",
                padding: "1rem",
                borderRadius: "0.5rem",
                backgroundColor: "#232428",
                border: "1px solid #303136",
              }}
            >
              <span style={{ color: "#9ba3af", fontSize: "0.9rem", textTransform: "uppercase" }}>
                Active Days (30d)
              </span>
              <div style={{ fontSize: "1.8rem", fontWeight: 600 }}>
                {activeDays}/{totalDays}
              </div>
              <span style={{ color: "#c5ccd5" }}>{formatPercent(activePercent)} active</span>
              <div style={{ color: "#9ba3af", fontSize: "0.85rem" }}>
                Keep logging to extend your streaks and improve consistency.
              </div>
            </div>
          </div>

          <div style={sectionGridStyle}>
            <div
              style={{
                display: "flex",
                flexDirection: "column",
                gap: "1rem",
                padding: "1rem",
                borderRadius: "0.5rem",
                backgroundColor: "#232428",
                border: "1px solid #303136",
              }}
            >
              <span style={{ color: "#9ba3af", fontSize: "0.9rem", textTransform: "uppercase" }}>
                Activity Distribution
              </span>
              <div style={{ display: "flex", gap: "1.5rem", alignItems: "center", flexWrap: "wrap" }}>
                <div
                  style={{
                    width: 160,
                    height: 160,
                    borderRadius: "50%",
                    background: pieBackground,
                    border: "8px solid #1f2024",
                    minWidth: 160,
                  }}
                />
                <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                  {distributionWithColors.length === 0 && (
                    <span style={{ color: "#9ba3af", fontStyle: "italic" }}>No activity entries</span>
                  )}
                  {distributionWithColors.map((item) => (
                    <div
                      key={item.category}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: "0.6rem",
                        fontSize: "0.95rem",
                      }}
                    >
                      <span
                        style={{
                          width: 12,
                          height: 12,
                          borderRadius: "2px",
                          display: "inline-block",
                          backgroundColor: item.color,
                        }}
                      />
                      <span style={{ flex: 1 }}>{item.category}</span>
                      <span style={{ color: "#9ba3af" }}>
                        {item.count} · {formatPercent(item.percent)}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            <div
              style={{
                display: "flex",
                flexDirection: "column",
                gap: "1rem",
                padding: "1rem",
                borderRadius: "0.5rem",
                backgroundColor: "#232428",
                border: "1px solid #303136",
              }}
            >
              <span style={{ color: "#9ba3af", fontSize: "0.9rem", textTransform: "uppercase" }}>
                Goal Fulfillment Trend
              </span>
              <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
                <svg
                  viewBox={`0 0 ${lineChart.width} ${lineChart.height}`}
                  role="img"
                  aria-label="Average goal fulfillment for last 7 and 30 days"
                  style={{ width: "100%", maxWidth: "18rem" }}
                >
                  <polyline
                    fill="none"
                    stroke="#3a7bd5"
                    strokeWidth="3"
                    points={lineChart.path}
                    strokeLinecap="round"
                  />
                  {lineChart.points.map((point) => (
                    <g key={point.label}>
                      <circle cx={point.x} cy={point.y} r="4" fill="#3a7bd5" />
                      <text
                        x={point.x}
                        y={lineChart.height - 6}
                        textAnchor="middle"
                        fill="#9ba3af"
                        fontSize="0.75rem"
                      >
                        {point.label}
                      </text>
                      <text
                        x={point.x}
                        y={point.y - 10}
                        textAnchor="middle"
                        fill="#e6e6e6"
                        fontSize="0.75rem"
                      >
                        {formatPercent(point.value)}
                      </text>
                    </g>
                  ))}
                </svg>
                <span style={{ color: "#9ba3af", fontSize: "0.85rem" }}>
                  Stable averages mean you are meeting goals consistently. Keep an eye on the 7-day trend for
                  short-term momentum.
                </span>
              </div>
            </div>
          </div>

          <div style={sectionGridStyle}>
            <div
              style={{
                display: "flex",
                flexDirection: "column",
                gap: "0.75rem",
                padding: "1rem",
                borderRadius: "0.5rem",
                backgroundColor: "#232428",
                border: "1px solid #303136",
              }}
            >
              <span style={{ color: "#9ba3af", fontSize: "0.9rem", textTransform: "uppercase" }}>
                Positive vs Negative Entries
              </span>
              <div>
                <div style={dualBarContainer}>
                  <div
                    style={{
                      ...meterFillBase,
                      width: `${positiveWidth}%`,
                      backgroundColor: "#43cea2",
                    }}
                  />
                  <div
                    style={{
                      ...meterFillBase,
                      width: `${negativeWidth}%`,
                      backgroundColor: "#8b1e3f",
                    }}
                  />
                </div>
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    marginTop: "0.5rem",
                    fontSize: "0.95rem",
                    color: "#c5ccd5",
                  }}
                >
                  <span>Positive: {positiveCount}</span>
                  <span>
                    Negative: {negativeCount} · Ratio {polarityRatio.toFixed(1)}x
                  </span>
                </div>
              </div>
              <span style={{ color: "#9ba3af", fontSize: "0.85rem" }}>
                Compare daily successes against underperforming entries to stay balanced.
              </span>
            </div>

            <div
              style={{
                display: "flex",
                flexDirection: "column",
                gap: "0.9rem",
                padding: "1.1rem",
                borderRadius: "0.5rem",
                backgroundColor: "#232428",
                border: "1px solid #303136",
              }}
            >
              <span style={{ color: "#9ba3af", fontSize: "0.9rem", textTransform: "uppercase" }}>
                Category Averages (excludes today)
              </span>
              {!activeAvgCategory && (
                <span style={{ color: "#9ba3af", fontStyle: "italic" }}>
                  Not enough entries to compute per-category averages.
                </span>
              )}
              {activeAvgCategory && (
                <div style={{ display: "flex", flexDirection: "column", gap: "0.9rem" }}>
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      gap: "0.75rem",
                    }}
                  >
                    <span style={{ fontSize: "1rem", fontWeight: 600 }}>{activeAvgCategory.category}</span>
                    <div style={{ display: "flex", gap: "0.35rem" }}>
                      <button
                        type="button"
                        onClick={() => setAvgCategoryIndex((prev) => prev - 1)}
                        style={{
                          ...navButtonStyle,
                          opacity: avgCategoryLength > 1 ? 1 : 0.5,
                          cursor: avgCategoryLength > 1 ? "pointer" : "default",
                        }}
                        disabled={avgCategoryLength <= 1}
                        aria-label="Previous category average"
                      >
                        ◀
                      </button>
                      <button
                        type="button"
                        onClick={() => setAvgCategoryIndex((prev) => prev + 1)}
                        style={{
                          ...navButtonStyle,
                          opacity: avgCategoryLength > 1 ? 1 : 0.5,
                          cursor: avgCategoryLength > 1 ? "pointer" : "default",
                        }}
                        disabled={avgCategoryLength <= 1}
                        aria-label="Next category average"
                      >
                        ▶
                      </button>
                    </div>
                  </div>
                  <div
                    style={{
                      display: "grid",
                      gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
                      gap: "0.75rem",
                    }}
                  >
                    <div
                      style={{
                        backgroundColor: "#1f2024",
                        borderRadius: "0.4rem",
                        padding: "0.75rem",
                        display: "flex",
                        flexDirection: "column",
                        gap: "0.35rem",
                      }}
                    >
                      <span style={{ color: "#9ba3af", fontSize: "0.8rem" }}>Last 7 days</span>
                      <strong style={{ fontSize: "1.2rem" }}>
                        {formatPercent(activeAvgCategory.last_7_days)}
                      </strong>
                    </div>
                    <div
                      style={{
                        backgroundColor: "#1f2024",
                        borderRadius: "0.4rem",
                        padding: "0.75rem",
                        display: "flex",
                        flexDirection: "column",
                        gap: "0.35rem",
                      }}
                    >
                      <span style={{ color: "#9ba3af", fontSize: "0.8rem" }}>Last 30 days</span>
                      <strong style={{ fontSize: "1.2rem" }}>
                        {formatPercent(activeAvgCategory.last_30_days)}
                      </strong>
                    </div>
                  </div>
                  <span style={{ color: "#9ba3af", fontSize: "0.85rem" }}>
                    Swiping through categories reveals how each area trends over time without counting today's
                    progress.
                  </span>
                </div>
              )}
              {avgCategoryLength > 1 && (
                <span style={{ color: "#60646f", fontSize: "0.75rem" }}>
                  {normaliseIndex(avgCategoryIndex, avgCategoryLength) + 1} / {avgCategoryLength}
                </span>
              )}
            </div>
          </div>

          <div
            style={{
              display: "flex",
              flexDirection: "column",
              gap: "0.9rem",
              padding: "1.1rem",
              borderRadius: "0.5rem",
              backgroundColor: "#232428",
              border: "1px solid #303136",
            }}
          >
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                gap: "0.75rem",
                flexWrap: "wrap",
              }}
            >
              <span style={{ color: "#9ba3af", fontSize: "0.9rem", textTransform: "uppercase" }}>
                Top Consistent Activities by Category
              </span>
              {consistencyLength > 1 && (
                <div style={{ display: "flex", gap: "0.35rem" }}>
                  <button
                    type="button"
                    onClick={() => setConsistencyIndex((prev) => prev - 1)}
                    style={{
                      ...navButtonStyle,
                      opacity: canCycleConsistency ? 1 : 0.5,
                      cursor: canCycleConsistency ? "pointer" : "default",
                    }}
                    disabled={!canCycleConsistency}
                    aria-label="Previous category for consistent activities"
                  >
                    ◀
                  </button>
                  <button
                    type="button"
                    onClick={() => setConsistencyIndex((prev) => prev + 1)}
                    style={{
                      ...navButtonStyle,
                      opacity: canCycleConsistency ? 1 : 0.5,
                      cursor: canCycleConsistency ? "pointer" : "default",
                    }}
                    disabled={!canCycleConsistency}
                    aria-label="Next category for consistent activities"
                  >
                    ▶
                  </button>
                </div>
              )}
            </div>
            {!activeConsistencyBucket && (
              <span style={{ color: "#9ba3af", fontStyle: "italic" }}>
                Add more entries to surface consistency champions.
              </span>
            )}
            {activeConsistencyBucket && (
              <div style={{ display: "flex", flexDirection: "column", gap: "0.85rem" }}>
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "baseline",
                    gap: "0.75rem",
                    flexWrap: "wrap",
                  }}
                >
                  <strong style={{ fontSize: "1.1rem" }}>{activeConsistencyBucket.category}</strong>
                  {consistencyLength > 1 && (
                    <span style={{ color: "#60646f", fontSize: "0.75rem" }}>
                      {normaliseIndex(consistencyIndex, consistencyLength) + 1} / {consistencyLength}
                    </span>
                  )}
                </div>
                {activeConsistencyBucket.activities.length === 0 && (
                  <span style={{ color: "#9ba3af", fontStyle: "italic" }}>
                    No activities logged for this category yet.
                  </span>
                )}
                {activeConsistencyBucket.activities.map((item) => (
                  <div key={item.name} style={{ display: "flex", flexDirection: "column", gap: "0.4rem" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", fontWeight: 600 }}>
                      <span>{item.name}</span>
                      <span>{formatPercent(item.consistency_percent)}</span>
                    </div>
                    <div style={meterContainer}>
                      <div
                        style={{
                          ...meterFillBase,
                          width: `${Math.min(100, Math.max(0, toNumber(item.consistency_percent)))}%`,
                          backgroundColor: "#3a7bd5",
                        }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
