import React, { useCallback, useEffect, useMemo, useRef } from "react";
import { useDispatch, useSelector } from "react-redux";
import { styles } from "../styles/common";
import { formatError } from "../utils/errors";
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
    <div>
      {loading && rows.length > 0 && <Loading message="Refreshing day…" inline />}
      <div style={styles.rowBetween}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <button
            type="button"
            onClick={() => shiftDay(-1)}
            style={{ ...styles.button, padding: "6px 10px" }}
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
            style={styles.input}
          />
          <button
            type="button"
            onClick={() => shiftDay(1)}
            style={{ ...styles.button, padding: "6px 10px", opacity: date >= todayString ? 0.6 : 1 }}
            disabled={date >= todayString}
            aria-label="Next day"
          >
            ▶
          </button>
        </div>
        <div style={{ minWidth: 220, maxWidth: 320 }}>
          <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12, marginBottom: 4 }}>
            <span>Today progress</span>
            <span>
              {percentLabel}
              {ratioLabel && <span style={{ marginLeft: 6, color: "#9ba3af" }}>({ratioLabel})</span>}
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
        <div style={styles.flexRow}>
          {autoSaving && <div style={styles.loadingText}>💾 Auto-saving...</div>}
          {!autoSaving && dirtyCount > 0 && (
            <div style={styles.loadingText}>{dirtyCount} change(s) pending...</div>
          )}
        </div>
      </div>

      {loading && <div style={styles.loadingText}>⏳ Loading today&apos;s activities...</div>}

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
              <td style={{ width: 120 }}>
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
                  style={{ ...styles.input, width: "90%" }}
                  placeholder="Note (max 100 chars)"
                  disabled={autoSaving}
                />
              </td>
            </tr>
          ))}
          {!loading && rows.length === 0 && (
            <tr>
              <td colSpan={3} style={{ padding: "12px", color: "#888" }}>
                No activities for the selected day.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
