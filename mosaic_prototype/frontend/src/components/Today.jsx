import React, { useCallback, useEffect, useRef, useState } from "react";
import { fetchToday, addEntry, finalizeDay } from "../api";
import { styles } from "../styles/common";

export default function Today({ onDataChanged, onNotify }) {
  const [date, setDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [autoSaving, setAutoSaving] = useState(false);
  const [dirtyRowsState, setDirtyRowsState] = useState({});
  const dirtyRef = useRef({});
  const debounceRef = useRef(null);
  const SAVE_DEBOUNCE_MS = 600;

  const load = useCallback(async (targetDate) => {
    const effectiveDate = targetDate ?? date;
    setLoading(true);
    try {
      const data = await fetchToday(effectiveDate);
      setRows(
        data
          .map((r) => ({ ...r, value: r.value ?? 0, note: r.note ?? "" }))
          .sort((a, b) => (a.value > 0 ? 1 : -1))
      );
    } catch (err) {
      onNotify?.(`Failed to load day overview: ${err.message}`, "error");
      setRows([]);
    } finally {
      setLoading(false);
    }
  }, [date, onNotify]);

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
          onNotify?.(`Failed to finalize day: ${err.message}`, "error");
        }
      }
    };
    const interval = setInterval(checkFinalize, 60 * 1000);
    return () => clearInterval(interval);
  }, [date, onNotify]);

  const flushDirtyRows = useCallback(async () => {
    if (saving) return;
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
      onNotify?.(`Auto-save failed: ${err.message}`, "error");
      const restored = entries.reduce((acc, row) => {
        acc[row.name] = row;
        return acc;
      }, {});
      dirtyRef.current = restored;
      setDirtyRowsState(restored);
    } finally {
      setAutoSaving(false);
    }
  }, [date, onDataChanged, onNotify, saving]);

  const scheduleAutoSave = useCallback(() => {
    if (saving) return;
    if (debounceRef.current) {
      clearTimeout(debounceRef.current);
    }
    debounceRef.current = setTimeout(() => {
      flushDirtyRows();
    }, SAVE_DEBOUNCE_MS);
  }, [flushDirtyRows, saving]);

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

  const handleSaveAll = async () => {
    if (saving) return;
    if (debounceRef.current) {
      clearTimeout(debounceRef.current);
      debounceRef.current = null;
    }
    const pendingDirty = dirtyRef.current;
    dirtyRef.current = {};
    setDirtyRowsState({});

    setSaving(true);
    try {
      await Promise.all(
        rows.map((row) =>
          addEntry({
            date,
            activity: row.name,
            value: Number(row.value) || 0,
            note: row.note || "",
          })
        )
      );
      onNotify?.("Changes saved", "success");
      await onDataChanged?.();
      await load(date);
    } catch (err) {
      onNotify?.(`Failed to save changes: ${err.message}`, "error");
      dirtyRef.current = pendingDirty;
      setDirtyRowsState(pendingDirty);
    } finally {
      setSaving(false);
    }
  };

  const handleValueChange = (row, newValue) => {
    const updatedRow = { ...row, value: Number(newValue) || 0 };
    setRows((prev) => prev.map((p) => (p.name === row.name ? updatedRow : p)));
    markRowDirty(row.name, updatedRow);
  };

  const handleNoteChange = (row, newNote) => {
    const trimmed = newNote.slice(0, 100);
    const updatedRow = { ...row, note: trimmed };
    setRows((prev) => prev.map((p) => (p.name === row.name ? updatedRow : p)));
    markRowDirty(row.name, updatedRow);
  };

  const dirtyCount = Object.keys(dirtyRowsState).length;

  return (
    <div>
      <div style={styles.rowBetween}>
        <input
          type="date"
          value={date}
          onChange={(e) => {
            const newDate = e.target.value;
            handleDateChange(newDate);
          }}
          style={styles.input}
        />
        <div style={styles.flexRow}>
          {autoSaving && <div style={styles.loadingText}>💾 Auto-saving…</div>}
          {!autoSaving && dirtyCount > 0 && (
            <div style={styles.loadingText}>{dirtyCount} change(s) pending…</div>
          )}
          <button
            style={{ ...styles.button, opacity: saving ? 0.7 : 1 }}
            onClick={handleSaveAll}
            disabled={saving || rows.length === 0}
          >
            {saving ? "Saving..." : "Save all changes"}
          </button>
        </div>
      </div>

      {loading && <div style={styles.loadingText}>⏳ Loading today&apos;s activities…</div>}

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
              <td>{r.name}</td>
              <td style={{ width: 120 }}>
                <select
                  value={r.value}
                  onChange={(e) => {
                    handleValueChange(r, e.target.value);
                  }}
                  style={{ ...styles.input, width: "100%" }}
                  disabled={saving}
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
                  disabled={saving}
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
