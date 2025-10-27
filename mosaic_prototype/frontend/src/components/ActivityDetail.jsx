import React, { useEffect, useMemo, useState } from "react";
import { updateActivity } from "../api";
import { styles } from "../styles/common";

export default function ActivityDetail({ activity, onClose, onNotify, onDataChanged }) {
  const [category, setCategory] = useState(activity.category || "");
  const [frequencyPerDay, setFrequencyPerDay] = useState(activity.frequency_per_day || 1);
  const [frequencyPerWeek, setFrequencyPerWeek] = useState(activity.frequency_per_week || 1);
  const [description, setDescription] = useState(activity.description || "");
  const [isSaving, setIsSaving] = useState(false);

  const initialState = useMemo(
    () => ({
      category: activity.category || "",
      frequency_per_day: activity.frequency_per_day || 1,
      frequency_per_week: activity.frequency_per_week || 1,
      description: activity.description || "",
      goal: activity.goal ?? 0,
    }),
    [activity]
  );

  useEffect(() => {
    setCategory(initialState.category);
    setFrequencyPerDay(initialState.frequency_per_day);
    setFrequencyPerWeek(initialState.frequency_per_week);
    setDescription(initialState.description);
  }, [initialState]);

  const avgGoalPerDay = useMemo(() => {
    return ((Number(frequencyPerDay) || 0) * (Number(frequencyPerWeek) || 0)) / 7;
  }, [frequencyPerDay, frequencyPerWeek]);

  const hasChanges =
    category !== initialState.category ||
    frequencyPerDay !== initialState.frequency_per_day ||
    frequencyPerWeek !== initialState.frequency_per_week ||
    description !== initialState.description;

  const handleClose = async () => {
    if (!hasChanges || isSaving) {
      onClose();
      return;
    }

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

      await updateActivity(activity.id, {
        category: category.trim(),
        frequency_per_day: perDay,
        frequency_per_week: perWeek,
        goal: avgGoalPerDay,
        description: description.trim(),
      });
      onNotify?.("Activity updated", "success");
      await onDataChanged?.();
      onClose();
    } catch (err) {
      onNotify?.(`Failed to update activity: ${err.message}`, "error");
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div style={styles.card}>
      <div style={{ ...styles.rowBetween, alignItems: "flex-start" }}>
        <h3 style={{ margin: 0 }}>{activity.name} - overview</h3>
        <button
          style={{ ...styles.button, opacity: isSaving ? 0.7 : 1 }}
          onClick={handleClose}
          disabled={isSaving}
        >
          {hasChanges ? (isSaving ? "Saving..." : "Save") : "Close"}
        </button>
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 12, marginTop: 12 }}>
        <div>
          <label style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            <span style={{ fontWeight: 600 }}>Activity name</span>
            <input value={activity.name} readOnly style={{ ...styles.input}} />
          </label>
        </div>
        <div>
          <label style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            <span style={{ fontWeight: 600 }}>Category</span>
            <input
              type="text"
              value={category}
              onChange={e => setCategory(e.target.value)}
              style={styles.input}
            />
          </label>
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          <span style={{ fontWeight: 600 }}>Goal</span>
          <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
            <label style={{ display: "flex", flexDirection: "column", fontSize: 13 }}>
              <span>Per day</span>
              <select
                value={frequencyPerDay}
                onChange={e => setFrequencyPerDay(Number(e.target.value))}
                style={{ ...styles.input, width: 120 }}
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
                style={{ ...styles.input, width: 120 }}
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
        </div>
        <div>
          <label style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            <span style={{ fontWeight: 600 }}>Description</span>
            <textarea
              value={description}
              onChange={e => setDescription(e.target.value)}
              rows={3}
              style={{ ...styles.input, resize: "vertical" }}
            />
          </label>
        </div>
      </div>
      {hasChanges && (
        <button
          style={{ ...styles.button, marginTop: 12, backgroundColor: "#b0b0b0" }}
          onClick={onClose}
          disabled={isSaving}
        >
          Not Save
        </button>
      )}
    </div>
  );
}
