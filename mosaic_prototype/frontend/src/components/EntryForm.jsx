import React, { useState } from 'react';
import { styles } from '../styles/common';

export default function EntryForm({ onSave, activities = [] }) {
  const [date, setDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [activity, setActivity] = useState('');
  const [value, setValue] = useState(0);
  const [note, setNote] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    onSave({ date, activity, value: parseFloat(value) || 0, note: note.trim() });
    setDate(new Date().toISOString().slice(0, 10));
    setActivity('first');
    setValue(0);
    setNote('');
  };

  return (
    <form onSubmit={handleSubmit} style={styles.form}>
      <input
        type="date"
        value={date}
        onChange={e => setDate(e.target.value)}
        required
        style={{ ...styles.input, width: "15%" }}
      />
      <select
        value={activity}
        onChange={e => setActivity(e.target.value)}
        style={{ ...styles.input, width: "20%" }}
        required
      >
        <option value="">Select activity...</option>
        {activities.map(a => (
          <option key={a.id} value={a.name}>{a.name}</option>
        ))}
      </select>
      <select
        type="number"
        value={value}
        onChange={e => setValue(e.target.value)}
        style={{ ...styles.input, width: "15%" }}
        required
      >
        {[0,1,2,3,4,5].map(v => <option key={v}>{v}</option>)}
      </select>
      <input
        type="text"
        placeholder="Note (max 100 chars)"
        value={note}
        onChange={e => setNote(e.target.value.slice(0, 100))}
        style={{ ...styles.input, width: "35%" }}
      />
      <button type="submit" style={{ ...styles.button, marginLeft: "25px" }}>
        Enter
      </button>
    </form>
  );
}
