import React, { useMemo, useState } from 'react';
import { styles } from '../styles/common';
import { formatError } from '../utils/errors';

export default function ActivityForm({ onSave, onDataChanged, onNotify }) {
  const [name, setName] = useState('');
  const [category, setCategory] = useState('');
  const [frequencyPerDay, setFrequencyPerDay] = useState(1);
  const [frequencyPerWeek, setFrequencyPerWeek] = useState(1);
  const [description, setDescription] = useState('');
  const [isSaving, setIsSaving] = useState(false);

  const avgGoalPerDay = useMemo(() => {
    const day = Number(frequencyPerDay) || 0;
    const week = Number(frequencyPerWeek) || 0;
    return (day * week) / 7;
  }, [frequencyPerDay, frequencyPerWeek]);

  const resetForm = () => {
    setName('');
    setCategory('');
    setFrequencyPerDay(1);
    setFrequencyPerWeek(1);
    setDescription('');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!name.trim() || !category.trim()) return;
    if (isSaving) return;

    setIsSaving(true);
    try {
      const perDay = Number.parseInt(frequencyPerDay, 10);
      const perWeek = Number.parseInt(frequencyPerWeek, 10);
      if (Number.isNaN(perDay) || perDay < 1 || perDay > 3) {
        throw new Error("Frequency per day must be between 1 and 3");
      }
      if (Number.isNaN(perWeek) || perWeek < 1 || perWeek > 7) {
        throw new Error("Frequency per week must be between 1 and 7");
      }
      await onSave({
        name: name.trim(),
        category: category.trim(),
        frequency_per_day: perDay,
        frequency_per_week: perWeek,
        goal: avgGoalPerDay,
        description: description.trim(),
      });
      onNotify?.('Activity was created', 'success');
      await onDataChanged?.();
      resetForm();
    } catch (err) {
      onNotify?.(`Failed to create activity: ${formatError(err)}`, 'error');
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
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        <label style={{ display: "flex", flexDirection: "column", fontSize: 13 }}>
          <span>Per day</span>
          <select
            value={frequencyPerDay}
            onChange={e => setFrequencyPerDay(Number(e.target.value))}
            style={{ ...styles.input, width: 100 }}
          >
            {[1, 2, 3].map(v => (
              <option key={v} value={v}>{v}</option>
            ))}
          </select>
        </label>
        <label style={{ display: "flex", flexDirection: "column", fontSize: 13 }}>
          <span>Per week</span>
          <select
            value={frequencyPerWeek}
            onChange={e => setFrequencyPerWeek(Number(e.target.value))}
            style={{ ...styles.input, width: 100 }}
          >
            {[1, 2, 3, 4, 5, 6, 7].map(v => (
              <option key={v} value={v}>{v}</option>
            ))}
          </select>
        </label>
        <div style={{ display: "flex", flexDirection: "column", justifyContent: "flex-end", fontSize: 13 }}>
          <span style={{ fontWeight: 600 }}>Avg/day</span>
          <span>{avgGoalPerDay.toFixed(2)}</span>
        </div>
      </div>
    </form>
  );
}
