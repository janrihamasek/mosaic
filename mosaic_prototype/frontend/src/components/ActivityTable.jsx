import React, { useState } from 'react';
import { styles } from '../styles/common';

export default function ActivityTable({
  activities,
  onActivate,
  onDeactivate,
  onDelete,
  onOpenDetail,
  onDataChanged,
  onNotify,
  loading = false,
}) {
  const [actionId, setActionId] = useState(null);

  // jednotné volání akcí + notifikace
  const handleAction = async (actionFn, id, successMessage, errorVerb) => {
    if (!actionFn) return;
    setActionId(id);
    try {
      await actionFn(id);
      onNotify?.(successMessage, 'success');
      await onDataChanged?.();
    } catch (err) {
      onNotify?.(`Failed to ${errorVerb}: ${err.message}`, 'error');
    } finally {
      setActionId(null);
    }
  };

  // aktivní nahoře
  const sortedActivities = [...activities].sort((a, b) => b.active - a.active);

  return (
    <div>
      {loading && <div style={styles.loadingText}>⏳ Loading activities…</div>}

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
                    onClick={() => handleAction(onDeactivate, a.id, "Activity deactivated", "deactivate activity")}
                    style={{ ...styles.button, opacity: actionId === a.id ? 0.6 : 1 }}
                    disabled={actionId === a.id}
                  >
                    {actionId === a.id ? "Working…" : "Deactivate"}
                  </button>
                ) : (
                  <>
                    <button
                      onClick={() => handleAction(onActivate, a.id, "Activity activated", "activate activity")}
                      style={{ ...styles.button, opacity: actionId === a.id ? 0.6 : 1 }}
                      disabled={actionId === a.id}
                    >
                      {actionId === a.id ? "Working…" : "Activate"}
                    </button>
                    <button
                      onClick={() => handleAction(onDelete, a.id, "Activity was deleted", "delete activity")}
                      style={{ ...styles.button, opacity: actionId === a.id ? 0.6 : 1 }}
                      disabled={actionId === a.id}
                    >
                      {actionId === a.id ? "Working…" : "Delete"}
                    </button>
                  </>
                )}
              </td>
            </tr>
          ))}
          {!loading && sortedActivities.length === 0 && (
            <tr>
              <td colSpan={4} style={{ padding: "12px", color: "#888" }}>
                No activities to display.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
