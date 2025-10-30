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
  const loading = status === "loading";
  const autoSaving = savingStatus === "loading";
  const dirtyCount = Object.keys(dirty || {}).length;
  const dirtyRef = useRef(dirty || {});
  const debounceRef = useRef(null);
  const SAVE_DEBOUNCE_MS = 600;

  useEffect(() => {
    dirtyRef.current = dirty || {};
  }, [dirty]);

  useEffect(() => {
    dispatch(loadToday(date));
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

  const scheduleAutoSave = useCallback(() => {
    if (autoSaving) return;
    if (debounceRef.current) {
      clearTimeout(debounceRef.current);
    }
    debounceRef.current = setTimeout(() => {
      flushDirtyRows();
    }, SAVE_DEBOUNCE_MS);
  }, [autoSaving, flushDirtyRows]);

  const handleValueChange = (row, newValue) => {
    dispatch(
      updateTodayRow({
        name: row.name,
        changes: { value: Number(newValue) || 0 },
      })
    );
    scheduleAutoSave();
  };

  const handleNoteChange = (row, newNote) => {
    dispatch(
      updateTodayRow({
        name: row.name,
        changes: { note: newNote.slice(0, 100) },
      })
    );
    scheduleAutoSave();
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
        return {
          totalValue: acc.totalValue + value,
          totalGoal: acc.totalGoal + goal,
        };
      },
      { totalValue: 0, totalGoal: 0 }
    );
  }, [rows]);

  const rawPercent =
    progressStats.totalGoal > 0 ? (progressStats.totalValue / progressStats.totalGoal) * 100 : 0;
  const cappedPercent = progressStats.totalGoal > 0 ? Math.min(rawPercent, 100) : 0;
  const percentLabel =
    progressStats.totalGoal > 0 ? `${Math.round(rawPercent)}%` : "N/A";
  const ratioLabel =
    progressStats.totalGoal > 0
      ? `${progressStats.totalValue.toFixed(1)} / ${progressStats.totalGoal.toFixed(1)}`
      : "";
  const progressColor = rawPercent >= 50 ? styles.highlightRow.backgroundColor : "#8b1e3f";
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
          {rows.map((r, idx) => (
            <div
              key={r.activity_id ?? idx}
              style={{
                ...styles.card,
                margin: 0,
                padding: "1rem",
                gap: "0.75rem",
                backgroundColor: r.value > 0 ? styles.highlightRow.backgroundColor : styles.card.backgroundColor,
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
                    style={{ ...styles.input, ...styles.inputMobile }}
                    placeholder="Note (max 100 chars)"
                    disabled={autoSaving}
                  />
                </label>
              </div>
            </div>
          ))}
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
          {rows.map((r, idx) => (
            <tr
              key={r.activity_id ?? idx}
              style={{
                ...styles.tableRow,
                ...(r.value > 0 ? styles.highlightRow : {}),
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
                  style={{ ...styles.input, width: "100%" }}
                  placeholder="Note (max 100 chars)"
                  disabled={autoSaving}
                />
              </td>
            </tr>
          ))}
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
            gap: "0.5rem",
            padding: isCompact ? "0.75rem" : 0,
            backgroundColor: isCompact ? "#202125" : "transparent",
            borderRadius: isCompact ? "0.5rem" : 0,
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.8125rem", color: "#9ba3af" }}>
            <span>Today progress</span>
            <span>
              {percentLabel}
              {ratioLabel && <span style={{ marginLeft: "0.375rem" }}>({ratioLabel})</span>}
            </span>
          </div>
          <div style={{ height: 8, backgroundColor: "#333", borderRadius: 4, overflow: "hidden" }}>
            <div
              style={{
                width: `${cappedPercent}%`,
                backgroundColor: progressColor,
                height: "100%",
                transition: "width 0.3s ease",
              }}
              aria-label="Today progress"
              role="progressbar"
              aria-valuemin={0}
              aria-valuemax={progressStats.totalGoal > 0 ? progressStats.totalGoal : undefined}
              aria-valuenow={progressStats.totalGoal > 0 ? progressStats.totalValue : undefined}
            />
          </div>
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
