import React, { useState } from 'react';
import { styles } from '../styles/common';

export default function ActivityForm({ onSave, onDataChanged, onNotify }) {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [isSaving, setIsSaving] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!name.trim()) return;
    if (isSaving) return;

    setIsSaving(true);
    try {
      await onSave({ name: name.trim(), description: description.trim() });
      onNotify?.('Activity was created', 'success');
      await onDataChanged?.();
      setName('');
      setDescription('');
    } catch (err) {
      onNotify?.(`Failed to create activity: ${err.message}`, 'error');
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} style={styles.form}>
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
