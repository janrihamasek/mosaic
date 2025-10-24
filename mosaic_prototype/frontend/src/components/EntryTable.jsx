import React, { useState } from 'react';
import { styles } from '../styles/common';

export default function EntryTable({ entries, onDelete }) {
  const [sortColumn, setSortColumn] = useState('date');
  const [sortDir, setSortDir] = useState('desc');

  const handleSort = (col) => {
    if (col === sortColumn) {
      setSortDir(sortDir === 'asc' ? 'desc' : 'asc');
    } else {
      setSortColumn(col);
      setSortDir('asc');
    }
  };

  const sortedEntries = [...entries].sort((a, b) => {
    let valA = a[sortColumn];
    let valB = b[sortColumn];
    if (sortColumn === 'value') {
      valA = Number(valA);
      valB = Number(valB);
    }
    if (valA < valB) return sortDir === 'asc' ? -1 : 1;
    if (valA > valB) return sortDir === 'asc' ? 1 : -1;
    return 0;
  });

  return (
    <table style={styles.table}>
      <thead>
        <tr style={styles.tableHeader}>
          <th onClick={() => handleSort('date')} style={{ cursor: "pointer" }}>Date</th>
          <th onClick={() => handleSort('activity')} style={{ cursor: "pointer" }}>Activity</th>
          <th onClick={() => handleSort('value')} style={{ cursor: "pointer" }}>Value</th>
          <th>Note</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        {sortedEntries.map((e, idx) => (
          <tr key={e.id ?? idx} style={styles.tableRow}>
            <td>{e.date}</td>
            <td>{e.activity}</td>
            <td>{e.value}</td>
            <td>{e.note}</td>
            <td style={{ width: "10%", textAlign: "right" }}>
              <button onClick={() => onDelete?.(e.id ?? idx)} style={styles.button}>
                Delete
              </button>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
