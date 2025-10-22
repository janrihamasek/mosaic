import React from 'react';
import { styles } from '../styles/common';

export default function ActivityTable({ activities, onDelete }) {
    return (
        <table style={styles.table}>
            <thead>
                <tr style={styles.tableHeader}>
                    <th style={{ width: "25%", textAlign: "left" }}>Name</th>
                    <th>Description</th>
                    <th></th>
                </tr>
            </thead>
            <tbody>
                {activities.map((c, idx) => (
                    <tr key={c.id ?? idx} style={styles.tableRow}>
                        <td>{c.name}</td>
                        <td>{c.description}</td>
                        <td style={{ width: "10%", textAlign: "right" }}>
                            <button
                                onClick={() => onDelete?.(c.id ?? idx)}
                                style={styles.button}
                            >
                                Delete
                            </button>
                        </td>
                    </tr>
                ))}
            </tbody>
        </table>
    );
}
