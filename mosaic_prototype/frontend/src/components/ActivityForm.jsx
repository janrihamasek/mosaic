import React, { useState } from 'react';
import { styles } from '../styles/common';

export default function ActivityForm({ onSave, onDataChanged }) {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [saved, setSaved] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!name.trim()) return;
    await onSave({ name: name.trim(), description: description.trim() });
    setSaved(true);
    setTimeout(() => setSaved(false), 3000);
    await onDataChanged?.();
    setName('');
    setDescription('');
  };

  return (
    <form onSubmit={handleSubmit} style={styles.form}>
      {saved && <div style={styles.successMessage}>✅ Activity was created</div>}
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
