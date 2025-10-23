import React, { useEffect, useState } from "react";
import { fetchToday, addEntry } from "../api";
import { styles } from "../styles/common";

export default function Today() {
  const [date, setDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [rows, setRows] = useState([]);

  const load = async (d = date) => {
    const data = await fetchToday(d);
    // zajistit defaulty
    setRows(data.map(r => ({
      ...r,
      value: r.value ?? 0,
      note: r.note ?? ""
    })));
  };

  useEffect(() => { load(); /* eslint-disable-next-line */ }, []);

  const handleSave = async (row) => {
    await addEntry({
      date,
      activity: row.name,
      value: Number(row.value) || 0,
      note: row.note || ""
    });
    await load();
  };

  return (
    <div>
      <div style={{ marginBottom: 12 }}>
        <input type="date" value={date} onChange={e => { setDate(e.target.value); load(e.target.value); }} style={styles.input}/>
      </div>
      <table style={styles.table}>
        <thead>
          <tr style={styles.tableHeader}>
            <th>Activity</th><th>Value</th><th>Note</th><th></th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r, idx) => (
            <tr key={r.activity_id ?? idx} style={styles.tableRow}>
              <td>{r.name}</td>
              <td style={{ width: 120 }}>
                <select value={r.value} onChange={(e) => {
                  const v = e.target.value;
                  setRows(prev => prev.map(p => p.name === r.name ? { ...p, value: v } : p));
                }} style={{ ...styles.input, width: "100%" }}>
                  <option>0</option><option>1</option><option>2</option>
                  <option>3</option><option>4</option><option>5</option>
                </select>
              </td>
              <td>
                <input value={r.note}
                  onChange={(e) => {
                    const v = e.target.value.slice(0, 100);
                    setRows(prev => prev.map(p => p.name === r.name ? { ...p, note: v } : p));
                  }}
                  style={{ ...styles.input, width: "100%" }} placeholder="Note (max 100 chars)"/>
              </td>
              <td style={{ width: 100, textAlign: "right" }}>
                <button style={styles.button} onClick={() => handleSave(r)}>Save</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
