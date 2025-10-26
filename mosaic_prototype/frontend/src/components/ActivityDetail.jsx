import React, { useEffect, useMemo, useState } from "react";
import { fetchEntries } from "../api";
import { styles } from "../styles/common";

export default function ActivityDetail({ activity, onClose, onNotify }) {
  const [entries, setEntries] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    (async () => {
      setLoading(true);
      try {
        const data = await fetchEntries();
        setEntries(data.filter(e => e.activity === activity.name));
      } catch (err) {
        onNotify?.(`Failed to load activity detail: ${err.message}`, 'error');
      } finally {
        setLoading(false);
      }
    })();
  }, [activity, onNotify]);

  const stats = useMemo(() => {
    if (!entries.length) return { count: 0, avg: 0, last: null };
    const values = entries.map(e => Number(e.value) || 0);
    const count = values.length;
    const avg = values.reduce((a, b) => a + b, 0) / count;
    const last = entries[0];
    return { count, avg, last };
  }, [entries]);

  return (
    <div style={styles.card}>
      <div style={styles.rowBetween}>
        <h3 style={{ margin: 0 }}>{activity.name} - overview</h3>
        <button style={styles.button} onClick={onClose}>Close</button>
      </div>
      <p style={{ marginTop: 8 }}><b>Category:</b> {activity.category || 'N/A'}</p>
      <p style={{ marginTop: 8 }}>{activity.description || 'N/A'}</p>
      {loading && <div style={styles.loadingText}>⏳ Loading activity history...</div>}
      <ul style={{ marginTop: 8 }}>
        <li><b>Total entries:</b> {stats.count}</li>
        <li><b>Average value:</b> {stats.avg.toFixed(2)}</li>
        <li><b>Last entry:</b> {stats.last ? `${stats.last.date} (value ${stats.last.value})` : 'N/A'}</li>
      </ul>
    </div>
  );
}
