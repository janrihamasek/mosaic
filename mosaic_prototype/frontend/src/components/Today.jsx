import React, { useCallback, useEffect, useState } from "react";
import { fetchToday, addEntry, finalizeDay } from "../api";
import { styles } from "../styles/common";

export default function Today({ onDataChanged, onNotify }) {
  const [date, setDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);

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

  const handleSaveAll = async () => {
    if (saving) return;
    setSaving(true);
    try {
      for (const row of rows) {
        await addEntry({
          date,
          activity: row.name,
          value: Number(row.value) || 0,
          note: row.note || "",
        });
      }
      onNotify?.("Changes saved", "success");
      await onDataChanged?.();
      await load(date);
    } catch (err) {
      onNotify?.(`Failed to save changes: ${err.message}`, "error");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div>
      <div style={styles.rowBetween}>
        <input
          type="date"
          value={date}
          onChange={(e) => {
            const newDate = e.target.value;
            setDate(newDate);
          }}
          style={styles.input}
        />
        <div style={styles.flexRow}>
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
                    const v = e.target.value;
                    setRows((prev) =>
                      prev.map((p) => (p.name === r.name ? { ...p, value: v } : p))
                    );
                  }}
                  style={{ ...styles.input, width: "100%" }}
                  disabled={saving}
                >
                  {[0, 1, 2, 3, 4, 5].map((v) => (
                    <option key={v}>{v}</option>
                  ))}
                </select>
              </td>
              <td>
                <input
                  value={r.note}
                  onChange={(e) => {
                    const v = e.target.value.slice(0, 100);
                    setRows((prev) =>
                      prev.map((p) => (p.name === r.name ? { ...p, note: v } : p))
                    );
                  }}
                  style={{ ...styles.input, width: "100%" }}
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
