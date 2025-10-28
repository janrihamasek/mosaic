import React, { useState } from "react";
import { styles } from "../styles/common";

export default function EntryTable({ entries, onDelete, onDataChanged, loading = false, onNotify }) {
  const [deletingId, setDeletingId] = useState(null);

  const handleDelete = async (id) => {
    if (deletingId !== null) return;
    setDeletingId(id);
    try {
      await onDelete?.(id);
      onNotify?.("Entry was deleted", "success");
      await onDataChanged?.();
    } catch (err) {
      onNotify?.(`Failed to delete entry: ${err.message}`, "error");
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <div>
      {loading && <div style={styles.loadingText}>⏳ Loading entries...</div>}

      <table style={styles.table}>
        <thead>
          <tr style={styles.tableHeader}>
            <th>Date</th>
            <th>Activity</th>
            <th>Category</th>
            <th>Goal</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {entries.map((entry, idx) => {
            const id = entry.id ?? idx;
            const goalValue = Number(entry.goal ?? 0);
            return (
              <tr key={id} style={styles.tableRow}>
                <td>{entry.date}</td>
                <td title={entry.category ? `Category: ${entry.category}` : "Category: N/A"}>{entry.activity}</td>
                <td>{entry.category || "N/A"}</td>
                <td>{goalValue ? goalValue.toFixed(2) : "0.00"}</td>
                <td style={{ width: "12%", textAlign: "right" }}>
                  <button
                    onClick={() => handleDelete(id)}
                    style={{ ...styles.button, backgroundColor : "#8b1e3f", opacity: deletingId === id ? 0.6 : 1 }}
                    disabled={deletingId === id}
                  >
                    {deletingId === id ? "Deleting..." : "Delete"}
                  </button>
                </td>
              </tr>
            );
          })}
          {!loading && entries.length === 0 && (
            <tr>
              <td colSpan={5} style={{ padding: "12px", color: "#888" }}>
                No entries to display.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
