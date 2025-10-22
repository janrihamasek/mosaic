import React from 'react';
import { styles } from '../styles/common';

export default function EntryTable({ entries, onDelete }) {
    return (
        <table style={styles.table}>
            <thead>
                <tr style={styles.tableHeader}>
                    <th>Date</th>
                    <th>Activity</th>
                    <th>Value</th>
                    <th>Note</th>
                </tr>
            </thead>
            <tbody>
                {entries.map((e, idx) => (
                    <tr key={e.id ?? idx} style={styles.tableRow}>
                        <td>{e.date}</td>
                        <td>{e.activity}</td>
                        <td>{e.value}</td>
                        <td>{e.note}</td>
                        <td style={{width: "10%", textAlign: "right"}}>
                            <button
                                onClick={() => onDelete?.(e.id ?? idx)}
                                style={styles.button}
                                aria-label={`Delete entry ${e.id ?? idx}`}
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
