import React, { useEffect, useMemo, useState } from "react";
import { fetchEntries } from "../api";
import { styles } from "../styles/common";

export default function ActivityDetail({ activity, onClose }) {
  const [entries, setEntries] = useState([]);

  useEffect(() => {
    (async () => {
      const data = await fetchEntries();
      setEntries(data.filter(e => e.activity === activity.name));
    })();
  }, [activity]);

  const stats = useMemo(() => {
    if (!entries.length) return { count: 0, avg: 0, last: null };
    const values = entries.map(e => Number(e.value) || 0);
    const count = values.length;
    const avg = values.reduce((a,b) => a+b, 0) / count;
    const last = entries[0]; // get_entries je ORDER BY date DESC – poslední záznam
    return { count, avg, last };
  }, [entries]);

  return (
    <div style={{ border: "1px solid #ccc", padding: 16, borderRadius: 8, margin: "12px 0" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h3 style={{ margin: 0 }}>{activity.name} — overview</h3>
        <button style={styles.button} onClick={onClose}>Close</button>
      </div>
      <p style={{ marginTop: 8 }}>{activity.description}</p>
      <ul style={{ marginTop: 8 }}>
        <li><b>Total entries:</b> {stats.count}</li>
        <li><b>Average value:</b> {stats.avg.toFixed(2)}</li>
        <li><b>Last entry:</b> {stats.last ? `${stats.last.date} (value ${stats.last.value})` : '—'}</li>
      </ul>
    </div>
  );
}
