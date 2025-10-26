import React, { useState } from 'react';
import { styles } from '../styles/common';

export default function ActivityForm({ onSave, onDataChanged, onNotify }) {
  const [name, setName] = useState('');
  const [category, setCategory] = useState('');
  const [goal, setGoal] = useState('');
  const [description, setDescription] = useState('');
  const [isSaving, setIsSaving] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!name.trim() || !category.trim() || goal === '') return;
    if (isSaving) return;

    setIsSaving(true);
    try {
      const goalValue = Math.max(0, Math.floor(Number(goal)));
      if (Number.isNaN(goalValue)) {
        throw new Error("Goal must be a number");
      }
      await onSave({
        name: name.trim(),
        category: category.trim(),
        goal: goalValue,
        description: description.trim(),
      });
      onNotify?.('Activity was created', 'success');
      await onDataChanged?.();
      setName('');
      setCategory('');
      setGoal('');
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
        placeholder="Activity"
        value={name}
        onChange={e => setName(e.target.value)}
        required
        style={styles.input}
      />
      <input
        type="text"
        placeholder="Category"
        value={category}
        onChange={e => setCategory(e.target.value)}
        required
        style={styles.input}
      />
      <input
        type="number"
        min="0"
        step="1"
        placeholder="Goal"
        value={goal}
        onChange={e => setGoal(e.target.value)}
        required
        style={{ ...styles.input, width: "120px" }}
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
