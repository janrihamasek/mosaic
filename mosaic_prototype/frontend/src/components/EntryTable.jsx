import React from 'react';

export default function EntryTable({ entries }) {
    return (
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
                <tr style={{ backgroundColor: "#f0f0f0" }}>
                    <th>Datum</th>
                    <th>Kategorie</th>
                    <th>Hodnota</th>
                    <th>Poznámka</th>
                </tr>
            </thead>
            <tbody>
                {entries.map((e, idx) => (
                    <tr key={idx} style={{ borderBottom: "1px solid #ccc" }}>
                        <td>{e.date}</td>
                        <td>{e.category}</td>
                        <td>{e.value}</td>
                        <td>{e.note}</td>
                    </tr>
                ))}
            </tbody>
        </table>
    );
}
