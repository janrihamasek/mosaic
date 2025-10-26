import React, { useState } from 'react';
import { styles } from '../styles/common';

export default function EntryTable({ entries, onDelete, onDataChanged, loading = false, onNotify }) {
  const [sortColumn, setSortColumn] = useState('date');
  const [sortDir, setSortDir] = useState('desc');
  const [page, setPage] = useState(1);
  const [deletingId, setDeletingId] = useState(null);
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
    if (deletingId !== null) return;
    setDeletingId(id);
    try {
      await onDelete?.(id);
      onNotify?.('Entry was deleted', 'success');
      await onDataChanged?.();
    } catch (err) {
      onNotify?.(`Failed to delete entry: ${err.message}`, 'error');
    } finally {
      setDeletingId(null);
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

  const paginatedEntries = sortedEntries.slice(0, page * pageSize);

  return (
    <div>
      {loading && <div style={styles.loadingText}>⏳ Loading entries…</div>}

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
                <button
                  onClick={() => handleDelete(e.id ?? idx)}
                  style={{ ...styles.button, opacity: deletingId === (e.id ?? idx) ? 0.6 : 1 }}
                  disabled={deletingId === (e.id ?? idx)}
                >
                  {deletingId === (e.id ?? idx) ? 'Deleting…' : 'Delete'}
                </button>
              </td>
            </tr>
          ))}
          {!loading && paginatedEntries.length === 0 && (
            <tr>
              <td colSpan={5} style={{ padding: "12px", color: "#888" }}>
                No entries to display.
              </td>
            </tr>
          )}
        </tbody>
      </table>

      {entries.length > paginatedEntries.length && (
        <div style={{ textAlign: "center", marginTop: 10 }}>
          <button
            style={{ ...styles.button, opacity: loading ? 0.7 : 1 }}
            onClick={() => setPage(page + 1)}
            disabled={loading}
          >
            {loading ? 'Loading…' : 'Load more'}
          </button>
        </div>
      )}
    </div>
  );
}
