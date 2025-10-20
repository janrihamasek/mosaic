import React, { useState } from 'react';
import { styles } from '../styles/common';

export default function EntryForm({ onSave }) {
    const [date, setDate] = useState(() => new Date().toISOString().slice(0, 10)); // výchozí dnešní datum
    const [category, setCategory] = useState('first'); // výchozí volba
    const [value, setValue] = useState(0); // výchozí hodnota 0
    const [note, setNote] = useState(''); // prázdné poznámky

    const handleSubmit = (e) => {
        e.preventDefault();
        onSave({
            date,
            category,
            value: parseFloat(value) || 0,
            note: note.trim()
        });
        // reset hodnot po odeslání
        setDate(new Date().toISOString().slice(0, 10));
        setCategory('first');
        setValue(0);
        setNote('');
    };

    return (
        <form onSubmit={handleSubmit} style={{ marginBottom: "20px" }}>
            <input
                type="date"
                value={date}
                onChange={e => setDate(e.target.value)}
                required
                style={styles.input}
            />
            <select
                value={category}
                onChange={e => setCategory(e.target.value)}
                style={styles.input}
                required
            >
                <option value="first">First</option>
                <option value="second">Second</option>
                <option value="third">Third</option>
            </select>
            <input
                type="number"
                placeholder="Value"
                value={value}
                onChange={e => setValue(e.target.value)}
                min={0}
                step="1"
                style={styles.input}
                required
            />
            <input
                type="text"
                placeholder="Note (max 100 chars)"
                value={note}
                onChange={e => setNote(e.target.value.slice(0, 100))}
                style={styles.input}
            />
            <button type="submit" style={styles.button}>
                Enter
            </button>
        </form>
    );
}
