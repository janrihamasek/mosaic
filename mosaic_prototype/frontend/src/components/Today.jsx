import React, { useEffect, useState } from "react";
import { fetchToday, addEntry, finalizeDay } from "../api";
import { styles } from "../styles/common";

export default function Today({ onDataChanged }) {
  const [date, setDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [rows, setRows] = useState([]);
  const [saved, setSaved] = useState(false);

  const load = async (d = date) => {
    const data = await fetchToday(d);
    setRows(
      data
        .map(r => ({ ...r, value: r.value ?? 0, note: r.note ?? "" }))
        .sort((a, b) => (a.value > 0 ? 1 : -1))
    );
  };

  useEffect(() => {
    const checkFinalize = async () => {
      const now = new Date();
      const midnight = new Date();
      midnight.setHours(0, 0, 0, 0);
      if (now.getTime() - midnight.getTime() < 60 * 1000) {
        await finalizeDay(date);
      }
    };
    const interval = setInterval(checkFinalize, 60 * 1000);
    return () => clearInterval(interval);
  }, [date]);

  useEffect(() => {
    load();
  }, []);

  const handleSaveAll = async () => {
    for (const row of rows) {
      await addEntry({
        date,
        activity: row.name,
        value: Number(row.value) || 0,
        note: row.note || ""
      });
    }
    setSaved(true);
    await onDataChanged?.();
    setTimeout(() => setSaved(false), 3000);
    await load();
  };

  return (
    <div>
      <div style={styles.rowBetween}>
        <input
          type="date"
          value={date}
          onChange={e => { setDate(e.target.value); load(e.target.value); }}
          style={styles.input}
        />
        <div style={styles.flexRow}>
          {saved && <div style={styles.successMessage}>✅ Changes saved</div>}
          <button style={styles.button} onClick={handleSaveAll}>Save all changes</button>
        </div>
      </div>

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
                    setRows(prev => prev.map(p => p.name === r.name ? { ...p, value: v } : p));
                  }}
                  style={{ ...styles.input, width: "100%" }}
                >
                  {[0,1,2,3,4,5].map(v => <option key={v}>{v}</option>)}
                </select>
              </td>
              <td>
                <input
                  value={r.note}
                  onChange={(e) => {
                    const v = e.target.value.slice(0, 100);
                    setRows(prev => prev.map(p => p.name === r.name ? { ...p, note: v } : p));
                  }}
                  style={{ ...styles.input, width: "100%" }}
                  placeholder="Note (max 100 chars)"
                />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
