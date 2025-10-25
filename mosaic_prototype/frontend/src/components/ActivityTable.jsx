import React, { useState } from 'react';
import { styles } from '../styles/common';

export default function ActivityTable({
  activities,
  onActivate,
  onDeactivate,
  onDelete,
  onOpenDetail,
  onDataChanged,
}) {
  const [message, setMessage] = useState("");

  // jednotné volání akcí + notifikace
  const handleAction = async (actionFn, id, msg) => {
    if (!actionFn) return;
    await actionFn(id);
    setMessage(msg);
    setTimeout(() => setMessage(""), 3000);
    await onDataChanged?.();
  };

  // aktivní nahoře
  const sortedActivities = [...activities].sort((a, b) => b.active - a.active);

  return (
    <div>
      {message && <div style={styles.successMessage}>✅ {message}</div>}

      <table style={styles.table}>
        <thead>
          <tr style={styles.tableHeader}>
            <th>Name</th>
            <th>Description</th>
            <th>Status</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {sortedActivities.map((a) => (
            <tr key={a.id} style={styles.tableRow}>
              <td
                style={{ cursor: "pointer", textDecoration: "underline" }}
                onClick={() => onOpenDetail?.(a)}
              >
                {a.name}
              </td>
              <td>{a.description}</td>
              <td>{a.active ? "Active" : "Inactive"}</td>
              <td style={styles.tableCellActions}>
                {a.active ? (
                  <button
                    onClick={() => handleAction(onDeactivate, a.id, "Deactivated")}
                    style={styles.button}
                  >
                    Deactivate
                  </button>
                ) : (
                  <>
                    <button
                      onClick={() => handleAction(onActivate, a.id, "Activated")}
                      style={styles.button}
                    >
                      Activate
                    </button>
                    <button
                      onClick={() => handleAction(onDelete, a.id, "Activity was deleted")}
                      style={styles.button}
                    >
                      Delete
                    </button>
                  </>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
