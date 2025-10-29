import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { fetchToday, addEntry, finalizeDay } from "../api";
import { styles } from "../styles/common";
import { formatError } from "../utils/errors";

const toLocalDateString = (dateObj) => {
  const tzOffset = dateObj.getTimezoneOffset();
  const adjusted = new Date(dateObj.getTime() - tzOffset * 60000);
  return adjusted.toISOString().slice(0, 10);
};

export default function Today({ onDataChanged, onNotify }) {
  const [date, setDate] = useState(() => toLocalDateString(new Date()));
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(false);
  const [autoSaving, setAutoSaving] = useState(false);
  const [dirtyRowsState, setDirtyRowsState] = useState({});
  const dirtyRef = useRef({});
  const debounceRef = useRef(null);
  const SAVE_DEBOUNCE_MS = 600;

  const sortRows = useCallback((list) => {
    return [...list].sort((a, b) => {
      const aDone = Number(a.value) > 0 ? 1 : 0;
      const bDone = Number(b.value) > 0 ? 1 : 0;
      if (aDone !== bDone) {
        return aDone - bDone;
      }
      const catCompare = (a.category || "").localeCompare(b.category || "", undefined, {
        sensitivity: "base",
      });
      if (catCompare !== 0) {
        return catCompare;
      }
      return (a.name || "").localeCompare(b.name || "", undefined, { sensitivity: "base" });
    });
  }, []);

  const load = useCallback(async (targetDate) => {
    const effectiveDate = targetDate ?? date;
    setLoading(true);
    try {
      const data = await fetchToday(effectiveDate);
      const formatted = data.map((r) => {
        const goalValue = Number(r.goal ?? r.activity_goal ?? 0) || 0;
        return {
          ...r,
          category: r.category ?? "",
          value: r.value ?? 0,
          note: r.note ?? "",
          goal: goalValue,
        };
      });
      setRows(sortRows(formatted));
    } catch (err) {
      onNotify?.(`Failed to load day overview: ${formatError(err)}`, "error");
      setRows([]);
    } finally {
      setLoading(false);
    }
  }, [date, onNotify, sortRows]);

  useEffect(() => {
    load(date);
  }, [date, load]);

  useEffect(() => {
    const checkFinalize = async () => {
      const now = new Date();
      const midnight = new Date();
      midnight.setHours(0, 0, 0, 0);
      if (now.getTime() - midnight.getTime() < 60 * 1000) {
        try {
          await finalizeDay(date);
        } catch (err) {
          onNotify?.(`Failed to finalize day: ${formatError(err)}`, "error");
        }
      }
    };
    const interval = setInterval(checkFinalize, 60 * 1000);
    return () => clearInterval(interval);
  }, [date, onNotify]);

  const flushDirtyRows = useCallback(async () => {
    if (autoSaving) return;
    const entries = Object.values(dirtyRef.current);
    if (!entries.length) return;

    if (debounceRef.current) {
      clearTimeout(debounceRef.current);
      debounceRef.current = null;
    }

    setAutoSaving(true);
    dirtyRef.current = {};
    setDirtyRowsState({});

    try {
      await Promise.all(
        entries.map((row) =>
          addEntry({
            date,
            activity: row.name,
            value: Number(row.value) || 0,
            note: row.note || "",
          })
        )
      );
      onNotify?.("Changes auto-saved", "info");
      await onDataChanged?.();
    } catch (err) {
      onNotify?.(`Auto-save failed: ${formatError(err)}`, "error");
      const restored = entries.reduce((acc, row) => {
        acc[row.name] = row;
        return acc;
      }, {});
      dirtyRef.current = restored;
      setDirtyRowsState(restored);
    } finally {
      setAutoSaving(false);
    }
  }, [date, onDataChanged, onNotify, autoSaving]);

  const scheduleAutoSave = useCallback(() => {
    if (autoSaving) return;
    if (debounceRef.current) {
      clearTimeout(debounceRef.current);
    }
    debounceRef.current = setTimeout(() => {
      flushDirtyRows();
    }, SAVE_DEBOUNCE_MS);
  }, [flushDirtyRows, autoSaving]);

  useEffect(() => {
    return () => {
      if (debounceRef.current) {
        clearTimeout(debounceRef.current);
      }
    };
  }, []);

  const markRowDirty = useCallback(
    (rowName, updatedRow) => {
      setDirtyRowsState((prev) => {
        const next = { ...prev, [rowName]: updatedRow };
        dirtyRef.current = next;
        return next;
      });
      scheduleAutoSave();
    },
    [scheduleAutoSave]
  );

  const todayString = useMemo(() => toLocalDateString(new Date()), []);

  const handleDateChange = useCallback(
    async (newDate) => {
      if (debounceRef.current) {
        clearTimeout(debounceRef.current);
        debounceRef.current = null;
      }
      if (Object.keys(dirtyRef.current).length) {
        await flushDirtyRows();
      }
      setDate(newDate);
    },
    [flushDirtyRows]
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

  const handleValueChange = (row, newValue) => {
    const updatedRow = { ...row, value: Number(newValue) || 0 };
    setRows((prev) => sortRows(prev.map((p) => (p.name === row.name ? updatedRow : p))));
    markRowDirty(row.name, updatedRow);
  };

  const handleNoteChange = (row, newNote) => {
    const trimmed = newNote.slice(0, 100);
    const updatedRow = { ...row, note: trimmed };
    setRows((prev) => sortRows(prev.map((p) => (p.name === row.name ? updatedRow : p))));
    markRowDirty(row.name, updatedRow);
  };

  const dirtyCount = Object.keys(dirtyRowsState).length;
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

  return (
    <div>
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
