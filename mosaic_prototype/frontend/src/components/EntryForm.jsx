import React, { useState } from 'react';
import { styles } from '../styles/common';

export default function EntryForm({ onSave, onDataChanged, activities = [], onNotify }) {
  const [date, setDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [activity, setActivity] = useState('');
  const [value, setValue] = useState(0);
  const [note, setNote] = useState('');
  const [isSaving, setIsSaving] = useState(false);

  const selectedActivity = activities.find(a => a.name === activity);
  const activityTitle = selectedActivity?.category
    ? `Category: ${selectedActivity.category}`
    : "Category: N/A";

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (isSaving) return;

    setIsSaving(true);
    try {
      await onSave({ date, activity, value: parseFloat(value) || 0, note: note.trim() });
      onNotify?.('Entry was saved', 'success');
      await onDataChanged?.();
      setDate(new Date().toISOString().slice(0, 10));
      setActivity('');
      setValue(0);
      setNote('');
    } catch (err) {
      onNotify?.(`Failed to save entry: ${err.message}`, 'error');
    } finally {
      setIsSaving(false);
    }
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
        aria-label="Activity"
        title={activityTitle}
      >
        <option value="">Select activity...</option>
        {activities.map(a => (
          <option key={a.id} value={a.name}>
            {a.category ? `${a.category} - ${a.name}` : a.name}
          </option>
        ))}
      </select>
      <select
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
      <button
        type="submit"
        style={{ ...styles.button, opacity: isSaving ? 0.7 : 1 }}
        disabled={isSaving}
      >
        {isSaving ? 'Saving...' : 'Enter'}
      </button>
    </form>
  );
}
