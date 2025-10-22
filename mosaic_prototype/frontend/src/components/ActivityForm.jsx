import React, { useState } from 'react';
import { styles } from '../styles/common';

export default function ActivityForm({ onSave }) {
    const [name, setName] = useState('');
    const [description, setDescription] = useState('');

    const handleSubmit = (e) => {
        e.preventDefault();
        if (!name.trim()) return;
        onSave({ name: name.trim(), description: description.trim() });
        setName('');
        setDescription('');
    };

    return (
        <form onSubmit={handleSubmit} style={{ marginBottom: "20px" }}>
            <input
                type="text"
                placeholder="Activity name"
                value={name}
                onChange={e => setName(e.target.value)}
                required
                style={styles.input}
            />
            <input
                type="text"
                placeholder="Description (optional)"
                value={description}
                onChange={e => setDescription(e.target.value)}
                style={styles.input}
            />
            <button type="submit" style={styles.button}>
                Enter
            </button>
        </form>
    );
}
