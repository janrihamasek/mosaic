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

  const sortedActivities = [...activities].sort((a, b) => {
    if (a.active !== b.active) {
      return a.active ? -1 : 1;
    }
    const catCompare = (a.category || "").localeCompare(b.category || "", undefined, {
      sensitivity: "base",
    });
    if (catCompare !== 0) {
      return catCompare;
    }
    return (a.name || "").localeCompare(b.name || "", undefined, { sensitivity: "base" });
  });

  return (
    <div>
      {loading && <div style={styles.loadingText}>⏳ Loading activities...</div>}

      <table style={styles.table}>
        <thead>
          <tr style={styles.tableHeader}>
            <th>Activity</th>
            <th>Category</th>
            <th>Goal</th>
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
                title={a.category ? `Category: ${a.category}` : "Category: N/A"}
                onClick={() => onOpenDetail?.(a)}
              >
                {a.name}
              </td>
              <td>{a.category || "N/A"}</td>
              <td>{a.goal ?? 0}</td>
              <td>{a.description || "N/A"}</td>
              <td>{a.active ? "Active" : "Inactive"}</td>
              <td style={styles.tableCellActions}>
                {a.active ? (
                  <button
                    onClick={() => handleAction(onDeactivate, a.id, "Activity deactivated", "deactivate activity")}
                    style={{ ...styles.button, opacity: actionId === a.id ? 0.6 : 1 }}
                    disabled={actionId === a.id}
                  >
                    {actionId === a.id ? "Working..." : "Deactivate"}
                  </button>
                ) : (
                  <>
                    <button
                      onClick={() => handleAction(onActivate, a.id, "Activity activated", "activate activity")}
                      style={{ ...styles.button, opacity: actionId === a.id ? 0.6 : 1 }}
                      disabled={actionId === a.id}
                    >
                      {actionId === a.id ? "Working..." : "Activate"}
                    </button>
                    <button
                      onClick={() => handleAction(onDelete, a.id, "Activity was deleted", "delete activity")}
                      style={{ ...styles.button, opacity: actionId === a.id ? 0.6 : 1 }}
                      disabled={actionId === a.id}
                    >
                      {actionId === a.id ? "Working..." : "Delete"}
                    </button>
                  </>
                )}
              </td>
            </tr>
          ))}
          {!loading && sortedActivities.length === 0 && (
            <tr>
              <td colSpan={6} style={{ padding: "12px", color: "#888" }}>
                No activities to display.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
