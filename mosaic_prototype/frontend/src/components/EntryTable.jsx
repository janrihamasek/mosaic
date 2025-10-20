import React from 'react';

export default function EntryTable({ entries, onDelete }) {
    return (
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
                <tr style={{ backgroundColor: "#f0f0f0" }}>
                    <th>Datum</th>
                    <th>Kategorie</th>
                    <th>Hodnota</th>
                    <th>Poznámka</th>
                    <th>Akce</th>
                </tr>
            </thead>
            <tbody>
                {entries.map((e, idx) => (
                    <tr key={e.id ?? idx} style={{ borderBottom: "1px solid #ccc" }}>
                        <td>{e.date}</td>
                        <td>{e.category}</td>
                        <td>{e.value}</td>
                        <td>{e.note}</td>
                        <td style={{ textAlign: "right" }}>
                            <button
                                onClick={() => onDelete?.(e.id ?? idx)}
                                style={{
                                    background: "#e53935",
                                    color: "#fff",
                                    border: "none",
                                    padding: "6px 10px",
                                    borderRadius: 4,
                                    cursor: "pointer"
                                }}
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
