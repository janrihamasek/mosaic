import React, { useState } from 'react';
import { styles } from '../styles/common';

export default function EntryTable({ entries, onDelete, onDataChanged }) {
  const [sortColumn, setSortColumn] = useState('date');
  const [sortDir, setSortDir] = useState('desc');
  const [deleted, setDeleted] = useState(false);
  const [page, setPage] = useState(1);
  const pageSize = 20;

  const handleSort = (col) => {
    if (col === sortColumn) {
      setSortDir(sortDir === 'asc' ? 'desc' : 'asc');
    } else {
      setSortColumn(col);
      setSortDir('asc');
    }
  };

  const handleDelete = async (id) => {
    await onDelete?.(id);
    setDeleted(true);
    setTimeout(() => setDeleted(false), 3000);
    await onDataChanged?.();
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

  const paginatedEntries = sortedEntries.slice(0, page * pageSize);

  return (
    <div>
      {deleted && <div style={styles.successMessage}>✅ Entry was deleted</div>}

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
          {paginatedEntries.map((e, idx) => (
            <tr key={e.id ?? idx} style={styles.tableRow}>
              <td>{e.date}</td>
              <td>{e.activity}</td>
              <td>{e.value}</td>
              <td>{e.note}</td>
              <td style={{ width: "10%", textAlign: "right" }}>
                <button onClick={() => handleDelete(e.id ?? idx)} style={styles.button}>
                  Delete
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {entries.length > paginatedEntries.length && (
        <div style={{ textAlign: "center", marginTop: 10 }}>
          <button style={styles.button} onClick={() => setPage(page + 1)}>
            Load more
          </button>
        </div>
      )}
    </div>
  );
}
