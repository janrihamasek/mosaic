import React, { useState } from 'react';

export default function EntryForm({ onSave }) {
    const [date, setDate] = useState('');
    const [category, setCategory] = useState('');
    const [value, setValue] = useState('');
    const [note, setNote] = useState('');

    const handleSubmit = (e) => {
        e.preventDefault();
        onSave({ date, category, value: parseFloat(value), note });
        setDate('');
        setCategory('');
        setValue('');
        setNote('');
    };

    return (
        <form onSubmit={handleSubmit} style={{ marginBottom: "20px" }}>
            <input type="text" placeholder="Date (YYYY-MM-DD)" value={date} onChange={e => setDate(e.target.value)} required />
            <input type="text" placeholder="Category" value={category} onChange={e => setCategory(e.target.value)} />
            <input type="number" placeholder="Value" value={value} onChange={e => setValue(e.target.value)} />
            <input type="text" placeholder="Note" value={note} onChange={e => setNote(e.target.value)} />
            <button 
                type="submit" 
                style={{
                    marginLeft: "10px",
                    background: "#e53935",
                    color: "#fff",
                    border: "none",
                    padding: "6px 10px",
                    borderRadius: 4,
                    cursor: "pointer"
                }}
            >
                Enter
            </button>
        </form>
    );
}
