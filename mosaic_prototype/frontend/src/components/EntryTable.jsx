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
      setSortDir(col === 'date' ? 'desc' : 'asc');
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

  const stringCompare = (a = '', b = '') => a.localeCompare(b, undefined, { sensitivity: 'base' });
  const numberCompare = (a = 0, b = 0) => Number(a) - Number(b);
  const comparators = {
    date: (a, b) => stringCompare(a.date ?? '', b.date ?? ''),
    activity: (a, b) => stringCompare(a.activity ?? '', b.activity ?? ''),
    category: (a, b) => stringCompare(a.category ?? '', b.category ?? ''),
    value: (a, b) => numberCompare(a.value ?? 0, b.value ?? 0),
    note: (a, b) => stringCompare(a.note ?? '', b.note ?? ''),
  };

  const sortedEntries = [...entries].sort((a, b) => {
    const primaryComparator = comparators[sortColumn] || (() => 0);
    let result = primaryComparator(a, b);
    if (sortDir === 'desc') result *= -1;
    if (result !== 0) return result;

    const tieBreakers = [comparators.category, comparators.activity, comparators.date];
    for (const cmp of tieBreakers) {
      if (!cmp) continue;
      const tie = cmp(a, b);
      if (tie !== 0) return tie;
    }
    return 0;
  });

  const paginatedEntries = sortedEntries.slice(0, page * pageSize);

  return (
    <div>
      {loading && <div style={styles.loadingText}>⏳ Loading entries...</div>}

      <table style={styles.table}>
        <thead>
          <tr style={styles.tableHeader}>
            <th onClick={() => handleSort('date')} style={{ cursor: "pointer" }}>Date</th>
            <th onClick={() => handleSort('activity')} style={{ cursor: "pointer" }}>Activity</th>
            <th onClick={() => handleSort('category')} style={{ cursor: "pointer" }}>Category</th>
            <th onClick={() => handleSort('value')} style={{ cursor: "pointer" }}>Value</th>
            <th>Note</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {paginatedEntries.map((e, idx) => (
            <tr key={e.id ?? idx} style={styles.tableRow}>
              <td>{e.date}</td>
              <td title={e.category ? `Category: ${e.category}` : "Category: N/A"}>{e.activity}</td>
              <td>{e.category || 'N/A'}</td>
              <td>{Number(e.value ?? 0)}</td>
              <td>{e.note}</td>
              <td style={{ width: "10%", textAlign: "right" }}>
                <button
                  onClick={() => handleDelete(e.id ?? idx)}
                  style={{ ...styles.button, opacity: deletingId === (e.id ?? idx) ? 0.6 : 1 }}
                  disabled={deletingId === (e.id ?? idx)}
                >
                  {deletingId === (e.id ?? idx) ? 'Deleting...' : 'Delete'}
                </button>
              </td>
            </tr>
          ))}
          {!loading && paginatedEntries.length === 0 && (
            <tr>
              <td colSpan={6} style={{ padding: "12px", color: "#888" }}>
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
            {loading ? 'Loading...' : 'Load more'}
          </button>
        </div>
      )}
    </div>
  );
}
