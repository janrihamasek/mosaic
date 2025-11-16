import React, { useCallback, useEffect, useMemo, useRef } from "react";
import { useDispatch, useSelector } from "react-redux";
import { styles } from "../styles/common";
import { formatError } from "../utils/errors";
import { useCompactLayout } from "../utils/useBreakpoints";
import {
  selectTodayState,
  setTodayDate,
  loadToday,
  updateTodayRow,
  saveDirtyTodayRows,
  finalizeToday,
  selectStatsState,
  loadStats,
} from "../store/entriesSlice";
import Loading from "./Loading";
import ErrorState from "./ErrorState";

const toLocalDateString = (dateObj) => {
  const tzOffset = dateObj.getTimezoneOffset();
  const adjusted = new Date(dateObj.getTime() - tzOffset * 60000);
  return adjusted.toISOString().slice(0, 10);
};

export default function Today({ onNotify }) {
  const dispatch = useDispatch();
  const { date, rows, status, dirty, savingStatus, error: todayError } = useSelector(selectTodayState);
  const statsState = useSelector(selectStatsState);
  const loading = status === "loading";
  const autoSaving = savingStatus === "loading";
  const dirtyCount = Object.keys(dirty || {}).length;
  const dirtyRef = useRef(dirty || {});
  const debounceRef = useRef(null);
  const NOTE_SAVE_DELAY_MS = 5000;

  useEffect(() => {
    dirtyRef.current = dirty || {};
  }, [dirty]);

  useEffect(() => {
    if (!date) return;
    dispatch(loadToday(date));
    dispatch(loadStats({ date }));
  }, [dispatch, date]);

  useEffect(() => {
    const checkFinalize = async () => {
      const now = new Date();
      const midnight = new Date();
      midnight.setHours(0, 0, 0, 0);
      if (now.getTime() - midnight.getTime() < 60 * 1000) {
        try {
          await dispatch(finalizeToday(date)).unwrap();
        } catch (err) {
          onNotify?.(`Failed to finalize day: ${formatError(err)}`, "error");
        }
      }
    };
    const interval = setInterval(checkFinalize, 60 * 1000);
    return () => clearInterval(interval);
  }, [dispatch, date, onNotify]);

  useEffect(
    () => () => {
      if (debounceRef.current) {
        clearTimeout(debounceRef.current);
      }
    },
    []
  );

  const flushDirtyRows = useCallback(async () => {
    if (autoSaving) return;
    if (!Object.keys(dirtyRef.current || {}).length) return;
    if (debounceRef.current) {
      clearTimeout(debounceRef.current);
      debounceRef.current = null;
    }
    try {
      await dispatch(saveDirtyTodayRows()).unwrap();
      onNotify?.("Changes auto-saved", "info");
    } catch (err) {
      onNotify?.(`Auto-save failed: ${formatError(err)}`, "error");
    }
  }, [autoSaving, dispatch, onNotify]);

  const scheduleNoteAutoSave = useCallback(() => {
    if (autoSaving) return;
    if (debounceRef.current) {
      clearTimeout(debounceRef.current);
    }
    debounceRef.current = setTimeout(() => {
      flushDirtyRows();
    }, NOTE_SAVE_DELAY_MS);
  }, [autoSaving, flushDirtyRows]);

  const handleValueChange = (row, newValue) => {
    const numericValue = Number(newValue) || 0;
    if (numericValue === (Number(row.value) || 0)) {
      return;
    }
    dirtyRef.current = {
      ...dirtyRef.current,
      [row.name]: {
        ...row,
        value: numericValue,
      },
    };
    dispatch(
      updateTodayRow({
        name: row.name,
        changes: { value: numericValue },
      })
    );
    void flushDirtyRows();
  };

  const handleNoteChange = (row, newNote) => {
    const limitedNote = newNote.slice(0, 100);
    dirtyRef.current = {
      ...dirtyRef.current,
      [row.name]: {
        ...row,
        note: limitedNote,
      },
    };
    dispatch(
      updateTodayRow({
        name: row.name,
        changes: { note: limitedNote },
      })
    );
    scheduleNoteAutoSave();
  };

  const handleNoteKeyDown = (row, event) => {
    if (event.key !== "Enter") return;
    event.preventDefault();
    const trimmedNote = event.currentTarget.value.slice(0, 100);
    const pendingRow = dirtyRef.current?.[row.name];
    const latestNote = pendingRow ? pendingRow.note : row.note;
    if (!pendingRow && trimmedNote === latestNote) {
      return;
    }
    dirtyRef.current = {
      ...dirtyRef.current,
      [row.name]: {
        ...row,
        note: trimmedNote,
      },
    };
    dispatch(
      updateTodayRow({
        name: row.name,
        changes: { note: trimmedNote },
      })
    );
    void flushDirtyRows();
  };

  const todayString = useMemo(() => toLocalDateString(new Date()), []);

  const handleDateChange = useCallback(
    async (newDate) => {
      if (debounceRef.current) {
        clearTimeout(debounceRef.current);
        debounceRef.current = null;
      }
      if (Object.keys(dirtyRef.current || {}).length) {
        await flushDirtyRows();
      }
      dispatch(setTodayDate(newDate));
    },
    [dispatch, flushDirtyRows]
  );

  const shiftDay = useCallback(
    (offset) => {
      const base = new Date(`${date}T00:00:00`);
      if (Number.isNaN(base.getTime())) {
        return;
      }
      base.setDate(base.getDate() + offset);
      const next = toLocalDateString(base);
      if (offset > 0 && next > todayString) {
        return;
      }
      handleDateChange(next);
    },
    [date, handleDateChange, todayString]
  );

  const progressStats = useMemo(() => {
    return rows.reduce(
      (acc, row) => {
        const value = Number(row.value) || 0;
        const goal = Number(row.goal) || 0;
        if (row.activity_type === "negative") {
          return acc;
        }
        return {
          totalValue: acc.totalValue + value,
          totalGoal: acc.totalGoal + goal,
        };
      },
      { totalValue: 0, totalGoal: 0 }
    );
  }, [rows]);

  const statsDate = statsState?.date;
  const statsSnapshot = statsDate === date ? statsState?.snapshot : null;
  const statsGoal = Number(statsSnapshot?.goal_completion_today);
  const hasStatsGoal = Number.isFinite(statsGoal);
  const fallbackGoalPercent =
    progressStats.totalGoal > 0 ? (progressStats.totalValue / progressStats.totalGoal) * 100 : 0;
  const resolvedGoalPercent = hasStatsGoal ? statsGoal : fallbackGoalPercent;
  const clampedGoalPercent = Number.isFinite(resolvedGoalPercent)
    ? Math.max(0, Math.min(100, resolvedGoalPercent))
    : 0;
  const goalPercentLabel = Number.isFinite(resolvedGoalPercent)
    ? `${resolvedGoalPercent.toFixed(1)}%`
    : progressStats.totalGoal > 0
    ? `${fallbackGoalPercent.toFixed(1)}%`
    : "N/A";
  const ratioLabel =
    progressStats.totalGoal > 0
      ? `${progressStats.totalValue.toFixed(1)} / ${progressStats.totalGoal.toFixed(1)}`
      : null;
  const goalProgressColor = clampedGoalPercent >= 50 ? "#2f9e44" : "#8b1e3f";
  const streakLength = Number.isFinite(statsSnapshot?.streak_length)
    ? statsSnapshot.streak_length
    : null;
  const statsLoading = statsState?.status === "loading" && statsDate !== date;
  const selectedDateLabel = useMemo(() => {
    if (!date) return null;
    const parsed = new Date(`${date}T00:00:00`);
    if (Number.isNaN(parsed.getTime())) {
      return date;
    }
    return parsed.toLocaleDateString();
  }, [date]);
  const { isCompact, isDesktop } = useCompactLayout();

  const navigationButtonStyle = {
    ...styles.button,
    padding: "0.4rem 0.65rem",
    fontSize: "0.9rem",
    ...(isCompact ? { width: "100%" } : {}),
  };

  const dateFieldStyle = {
    ...styles.input,
    minWidth: isCompact ? "100%" : "12rem",
    width: isCompact ? "100%" : "12rem",
  };

  const summaryGridStyle = {
    display: "grid",
    gridTemplateColumns: isDesktop ? "minmax(0, auto) minmax(0, 1fr) minmax(0, auto)" : "1fr",
    gap: isCompact ? "0.75rem" : "1rem",
    alignItems: isDesktop ? "center" : "stretch",
  };

  const statusMessageStyle = {
    ...styles.loadingText,
    marginTop: 0,
    display: "flex",
    alignItems: "center",
    gap: "0.5rem",
  };

  const renderActivityContent = () => {
    if (isCompact) {
      return (
        <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
          {rows.map((r, idx) => {
            const highlightStyle =
              Number(r.value) > 0
                ? r.activity_type === "negative"
                  ? styles.negativeRow
                  : styles.positiveRow
                : {};
            return (
              <div
                key={r.activity_id ?? idx}
                style={{
                  ...styles.card,
                  margin: 0,
                  padding: "1rem",
                  gap: "0.75rem",
                  ...highlightStyle,
                }}
              >
              <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "space-between", gap: "0.5rem" }}>
                <span style={{ ...styles.textHeading, fontSize: "1.125rem" }}>{r.name}</span>
                <span style={{ ...styles.textMuted, fontSize: "0.8125rem" }}>
                  {r.category ? `Category: ${r.category}` : "Category: N/A"}
                </span>
              </div>
              <div style={{ display: "grid", gap: "0.75rem" }}>
                <label style={{ display: "flex", flexDirection: "column", gap: "0.35rem" }}>
                  <span style={{ ...styles.textMuted, fontSize: "0.75rem" }}>Value</span>
                  <select
                    value={r.value}
                    onChange={(e) => {
                      handleValueChange(r, e.target.value);
                    }}
                    style={{ ...styles.input, ...styles.inputMobile }}
                    disabled={autoSaving}
                  >
                    {[0, 1, 2, 3, 4, 5].map((v) => (
                      <option key={v} value={v}>
                        {v}
                      </option>
                    ))}
                  </select>
                </label>
                <label style={{ display: "flex", flexDirection: "column", gap: "0.35rem" }}>
                  <span style={{ ...styles.textMuted, fontSize: "0.75rem" }}>Note</span>
                  <input
                    value={r.note}
                    onChange={(e) => {
                      handleNoteChange(r, e.target.value);
                    }}
                    onKeyDown={(e) => {
                      handleNoteKeyDown(r, e);
                    }}
                    style={{ ...styles.input, ...styles.inputMobile }}
                    placeholder="Note (max 100 chars). For save Note press Enter"
                    disabled={autoSaving}
                  />
                </label>
              </div>
            </div>
            );
          })}
          {!loading && rows.length === 0 && (
            <div style={{ ...styles.card, margin: 0, padding: "1rem", color: "#9ba3af", fontStyle: "italic" }}>
              No activities for the selected day.
            </div>
          )}
        </div>
      );
    }

    return (
      <table style={styles.table}>
        <thead>
          <tr style={styles.tableHeader}>
            <th>Activity</th>
            <th>Value</th>
            <th>Note</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r, idx) => {
            const highlightStyle =
              Number(r.value) > 0
                ? r.activity_type === "negative"
                  ? styles.negativeRow
                  : styles.positiveRow
                : {};
            return (
              <tr
                key={r.activity_id ?? idx}
                style={{
                  ...styles.tableRow,
                  ...highlightStyle,
                }}
              >
              <td title={r.category ? `Category: ${r.category}` : "Category: N/A"}>{r.name}</td>
              <td style={{ width: "12rem" }}>
                <select
                  value={r.value}
                  onChange={(e) => {
                    handleValueChange(r, e.target.value);
                  }}
                  style={{ ...styles.input, width: "100%" }}
                  disabled={autoSaving}
                >
                  {[0, 1, 2, 3, 4, 5].map((v) => (
                    <option key={v} value={v}>
                      {v}
                    </option>
                  ))}
                </select>
              </td>
              <td>
                <input
                  value={r.note}
                  onChange={(e) => {
                    handleNoteChange(r, e.target.value);
                  }}
                  onKeyDown={(e) => {
                    handleNoteKeyDown(r, e);
                  }}
                  style={{ ...styles.input, width: "100%" }}
                  placeholder="Note (max 100 chars). For save Note press Enter"
                  disabled={autoSaving}
                />
              </td>
            </tr>
            );
          })}
          {!loading && rows.length === 0 && (
            <tr>
              <td colSpan={3} style={{ padding: "0.75rem", color: "#9ba3af", fontStyle: "italic" }}>
                No activities for the selected day.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    );
  };

  if (status === "failed") {
    const message = todayError?.friendlyMessage || todayError?.message || "Failed to load today view.";
    return (
      <ErrorState
        message={message}
        onRetry={() => dispatch(loadToday(date))}
        actionLabel="Retry load"
      />
    );
  }

  if (loading && rows.length === 0) {
    return <Loading message="Loading day overview…" />;
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
      {loading && rows.length > 0 && <Loading message="Refreshing day…" inline />}
      <div style={summaryGridStyle}>
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: "0.5rem",
          }}
        >
          <div
            style={{
              display: "grid",
              gridTemplateColumns: isCompact ? "repeat(3, minmax(0, 1fr))" : "auto auto auto",
              gap: "0.5rem",
              alignItems: "center",
              width: "100%",
            }}
          >
            <button
              type="button"
              onClick={() => shiftDay(-1)}
              style={navigationButtonStyle}
              aria-label="Previous day"
            >
              ◀
            </button>
            <input
              type="date"
              value={date}
              max={todayString}
              onChange={(e) => {
                const newDate = e.target.value;
                handleDateChange(newDate);
              }}
              style={{
                ...dateFieldStyle,
                ...(isCompact ? { gridColumn: "span 2" } : {}),
              }}
            />
            <button
              type="button"
              onClick={() => shiftDay(1)}
              style={{ ...navigationButtonStyle, opacity: date >= todayString ? 0.6 : 1 }}
              disabled={date >= todayString}
              aria-label="Next day"
            >
              ▶
            </button>
          </div>
          <div style={{ ...styles.textMuted, fontSize: "0.8125rem" }}>
            Use the date selector to review or adjust daily activity notes.
          </div>
        </div>
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: "0.75rem",
            padding: isCompact ? "0.9rem" : "1rem",
            backgroundColor: "#232428",
            borderRadius: "0.5rem",
            border: "1px solid #303136",
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "0.5rem" }}>
            <div style={{ display: "flex", flexDirection: "column", gap: "0.25rem" }}>
              <span
                style={{
                  fontSize: "0.8125rem",
                  color: "#9ba3af",
                  textTransform: "uppercase",
                }}
              >
                Goal Completion
              </span>
              {selectedDateLabel && (
                <span style={{ ...styles.textMuted, fontSize: "0.75rem", textTransform: "none" }}>
                  {selectedDateLabel}
                </span>
              )}
            </div>
            {statsLoading && <span style={{ ...styles.textMuted, fontSize: "0.75rem" }}>Loading…</span>}
          </div>
          <div style={{ fontSize: "2rem", fontWeight: 600 }}>{goalPercentLabel}</div>
          <div style={{ height: 8, backgroundColor: "#333", borderRadius: 4, overflow: "hidden" }}>
            <div
              style={{
                width: `${clampedGoalPercent}%`,
                backgroundColor: goalProgressColor,
                height: "100%",
                transition: "width 0.3s ease",
              }}
              aria-label="Goal completion today"
              role="progressbar"
              aria-valuemin={0}
              aria-valuemax={100}
              aria-valuenow={Number.isFinite(resolvedGoalPercent) ? Math.round(clampedGoalPercent) : undefined}
            />
          </div>
          {ratioLabel && (
            <span style={{ color: "#9ba3af", fontSize: "0.85rem" }}>
              Logged {ratioLabel} of the daily target
            </span>
          )}
          {typeof streakLength === "number" && (
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
          )}
        </div>
        <div style={{ display: "flex", justifyContent: isDesktop ? "flex-end" : "flex-start" }}>
          {autoSaving && <div style={styles.loadingText}>💾 Auto-saving...</div>}
          {!autoSaving && dirtyCount > 0 && (
            <div style={statusMessageStyle}>{dirtyCount} change(s) pending...</div>
          )}
        </div>
      </div>

      {loading && <div style={styles.loadingText}>⏳ Loading today&apos;s activities...</div>}

      {renderActivityContent()}
    </div>
  );
}
