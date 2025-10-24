import React from 'react';
import { styles } from '../styles/common';

export default function ActivityTable({ activities, onActivate, onDeactivate, onDelete, onOpenDetail }) {
  return (
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
        {activities.map((a) => (
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
                <button onClick={() => onDeactivate?.(a.id)} style={styles.button}>Deactivate</button>
              ) : (
                <>
                  <button onClick={() => onActivate?.(a.id)} style={styles.button}>Activate</button>
                  <button onClick={() => onDelete?.(a.id)} style={styles.button}>Delete</button>
                </>
              )}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
