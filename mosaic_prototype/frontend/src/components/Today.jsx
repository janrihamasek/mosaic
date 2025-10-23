import React, { useEffect, useState } from "react";
import { fetchToday, addEntry, finalizeDay } from "../api";
import { styles } from "../styles/common";

export default function Today() {
  const [date, setDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [rows, setRows] = useState([]);
  const [saved, setSaved] = useState(false);

  const load = async (d = date) => {
    const data = await fetchToday(d);
    setRows(
      data
        .map(r => ({
          ...r,
          value: r.value ?? 0,
          note: r.note ?? ""
        }))
        .sort((a, b) => (a.value > 0 ? 1 : -1))
    );
  };

  // automatická kontrola půlnoci
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
    setTimeout(() => setSaved(false), 3000);
    await load();
  };

  const handleSort = (col) => {
    setRows(prev => {
      const sorted = [...prev].sort((a, b) => {
        if (col === "value") return a.value - b.value;
        if (col === "activity") return a.name.localeCompare(b.name);
        return 0;
      });
      return sorted;
    });
  };

  return (
    <div>
      <div style={{ marginBottom: 12 }}>
        <input
          type="date"
          value={date}
          onChange={e => { setDate(e.target.value); load(e.target.value); }}
          style={styles.input}
        />
      </div>

      <table style={styles.table}>
        <thead>
          <tr style={styles.tableHeader}>
            <th onClick={() => handleSort("activity")} style={{ cursor: "pointer" }}>Activity</th>
            <th onClick={() => handleSort("value")} style={{ cursor: "pointer" }}>Value</th>
            <th>Note</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r, idx) => (
            <tr key={r.activity_id ?? idx}
                style={{
                  ...styles.tableRow,
                  backgroundColor: r.value > 0 ? "#d6f5d6" : "transparent"
                }}>
              <td>{r.name}</td>
              <td style={{ width: 120 }}>
                <select
                  value={r.value}
                  onChange={(e) => {
                    const v = e.target.value;
                    setRows(prev => prev.map(p => p.name === r.name ? { ...p, value: v } : p));
                  }}
                  style={{ ...styles.input, width: "100%" }}>
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

      <div style={{ marginTop: 16, textAlign: "right" }}>
        <button style={styles.button} onClick={handleSaveAll}>Save all changes</button>
        {saved && <div style={{ color: "green", marginTop: 8 }}>✅ Changes saved successfully</div>}
      </div>
    </div>
  );
}
