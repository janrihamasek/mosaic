import React, { useEffect, useMemo, useState } from "react";
import { useDispatch } from "react-redux";
import { styles } from "../styles/common";
import { formatError } from "../utils/errors";
import { updateActivityDetails } from "../store/activitiesSlice";
import ModalForm from "./shared/ModalForm";

export default function ActivityDetail({ activity, onClose: dismiss, onNotify }) {
  const dispatch = useDispatch();
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

  const handleSave = async () => {
    if (isSaving) return;
    if (!hasChanges) {
      dismiss();
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

      await dispatch(
        updateActivityDetails({
          id: activity.id,
          payload: {
            category: category.trim(),
            frequency_per_day: perDay,
            frequency_per_week: perWeek,
            goal: avgGoalPerDay,
            description: description.trim(),
          },
        })
      ).unwrap();
      onNotify?.("Activity updated", "success");
      dismiss();
    } catch (err) {
      onNotify?.(`Failed to update activity: ${formatError(err)}`, "error");
    } finally {
      setIsSaving(false);
    }
  };

  const handleDiscard = () => {
    if (isSaving) return;
    dismiss();
  };

  return (
    <ModalForm
      isOpen
      onClose={handleDiscard}
      title={activity.name}
      closeLabel={hasChanges ? "Not Save" : "Close"}
      isDismissDisabled={isSaving}
      footerContent={
        hasChanges ? (
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              gap: "0.75rem",
              flexWrap: "wrap",
            }}
          >
            <button
              type="button"
              style={{ ...styles.button, backgroundColor: "#3a3b3f" }}
              onClick={handleDiscard}
              disabled={isSaving}
            >
              Not Save
            </button>
            <button
              type="button"
              style={{ ...styles.button, backgroundColor: "#2f9e44" }}
              onClick={handleSave}
              disabled={isSaving}
            >
              {isSaving ? "Saving..." : "Save"}
            </button>
          </div>
        ) : null
      }
    >
      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        <div>
          <label style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            <span style={{ fontWeight: 600 }}>Activity name</span>
            <input value={activity.name} readOnly style={{ ...styles.input }} />
          </label>
        </div>
        <div>
          <label style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            <span style={{ fontWeight: 600 }}>Category</span>
            <input
              type="text"
              value={category}
              onChange={(e) => setCategory(e.target.value)}
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
                onChange={(e) => setFrequencyPerDay(Number(e.target.value))}
                style={{ ...styles.input, width: 120 }}
              >
                {[1, 2, 3].map((v) => (
                  <option key={v} value={v}>
                    {v}
                  </option>
                ))}
              </select>
            </label>
            <label style={{ display: "flex", flexDirection: "column", fontSize: 13 }}>
              <span>Per week</span>
              <select
                value={frequencyPerWeek}
                onChange={(e) => setFrequencyPerWeek(Number(e.target.value))}
                style={{ ...styles.input, width: 120 }}
              >
                {[1, 2, 3, 4, 5, 6, 7].map((v) => (
                  <option key={v} value={v}>
                    {v}
                  </option>
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
              onChange={(e) => setDescription(e.target.value)}
              rows={3}
              style={{ ...styles.input, resize: "vertical" }}
            />
          </label>
        </div>
      </div>
    </ModalForm>
  );
}
