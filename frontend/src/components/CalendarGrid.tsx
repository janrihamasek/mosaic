import React, { useEffect, useMemo, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { styles, VALENCE_COLORS, getValenceColor } from "../styles/common";
import {
  loadCalendarRange,
  saveCalendarEntry,
  selectCalendarRows,
  selectCalendarDays,
  selectCalendarSaving,
  selectCalendarStatus,
  selectCalendarState,
  updateCalendarCell,
} from "../store/entriesSlice";
import type { AppDispatch } from "../store";
import type { CalendarRow } from "../types/store";
import Loading from "./Loading";
import ErrorState from "./ErrorState";

interface CalendarGridProps {
  startDate: string;
  endDate: string;
  onNotify?: (message: string, type: "success" | "error" | "info") => void;
}

type ActiveCell = {
  activity: string;
  date: string;
};

const clampValue = (value: number) => Math.max(0, Math.min(99, value));

function getHeatmapColor(value: number, goal: number, activityType: string): string {
  if (!value || Number.isNaN(value)) {
    return "#2b2d33";
  }
  if (activityType === "negative") {
    return value > 0 ? "#6a1a29" : "#2b2d33";
  }
  if (activityType === "neutral") {
    return "#30404d";
  }
  const ratio = goal > 0 ? value / goal : value > 0 ? 0.6 : 0;
  if (ratio >= 1.5) return "#1f8a3b";
  if (ratio >= 1) return "#2f9e44";
  if (ratio >= 0.5) return "#3ca35b";
  return "#2f6f3a";
}

function dayLabel(dateStr: string) {
  const parsed = new Date(`${dateStr}T00:00:00`);
  const weekday = parsed.toLocaleDateString(undefined, { weekday: "short" });
  const day = parsed.getDate();
  return `${weekday} ${day}`;
}

function activityIsInactive(row: CalendarRow, day: string): boolean {
  if (row.active === false) return true;
  if (!row.deactivated_at) return false;
  return day >= row.deactivated_at;
}

export default function CalendarGrid({ startDate, endDate, onNotify }: CalendarGridProps) {
  const dispatch = useDispatch<AppDispatch>();
  const rows = useSelector(selectCalendarRows);
  const days = useSelector(selectCalendarDays);
  const saving = useSelector(selectCalendarSaving);
  const status = useSelector(selectCalendarStatus);
  const calendarState = useSelector(selectCalendarState);
  const [activeCell, setActiveCell] = useState<ActiveCell | null>(null);
  const [draftValue, setDraftValue] = useState<number>(0);
  const [draftNote, setDraftNote] = useState<string>("");

  useEffect(() => {
    dispatch(loadCalendarRange({ startDate, endDate }));
  }, [dispatch, startDate, endDate]);

  useEffect(() => {
    if (!activeCell) return;
    const row = rows.find((r) => r.name === activeCell.activity);
    const cell = row?.cells?.[activeCell.date];
    if (cell) {
      setDraftValue(Number(cell.value ?? 0));
      setDraftNote(cell.note || "");
    }
  }, [activeCell, rows]);

  const handleOpenEditor = (activity: string, date: string) => {
    setActiveCell({ activity, date });
  };

  const handleCloseEditor = () => {
    setActiveCell(null);
  };

  const handleSaveCell = async () => {
    if (!activeCell) return;
    const value = clampValue(Number.isNaN(draftValue) ? 0 : draftValue);
    const note = draftNote.slice(0, 100);
    dispatch(
      updateCalendarCell({
        activity: activeCell.activity,
        date: activeCell.date,
        value,
        note,
      })
    );
    try {
      await dispatch(
        saveCalendarEntry({
          activity: activeCell.activity,
          date: activeCell.date,
          value,
          note,
        })
      ).unwrap();
      onNotify?.("Saved entry", "success");
      handleCloseEditor();
    } catch (error: any) {
      onNotify?.(
        error?.friendlyMessage || error?.message || "Failed to save entry",
        "error"
      );
    }
  };

  const renderCell = (row: CalendarRow, day: string) => {
    const cell = row.cells[day] || { value: 0, note: "" };
    const inactive = activityIsInactive(row, day);
    const isEditing =
      activeCell?.activity === row.name && activeCell?.date === day;
    const savingKey = `${row.name}__${day}`;
    const isSaving = saving[savingKey];

    const backgroundColor = inactive
      ? "#1f2024"
      : getHeatmapColor(Number(cell.value ?? 0), row.goal, row.activity_type);

    return (
      <td
        key={`${row.name}-${day}`}
        style={{
          padding: 0,
          position: "relative",
          border: "1px solid #2f3338",
          backgroundColor,
          minWidth: 48,
          textAlign: "center",
          color: inactive ? "#6b7280" : "#e5e7eb",
        }}
      >
        <button
          type="button"
          onClick={() => handleOpenEditor(row.name, day)}
          style={{
            width: "100%",
            height: "100%",
            padding: "0.45rem 0.35rem",
            background: "transparent",
            border: "none",
            color: "inherit",
            fontWeight: 600,
            cursor: inactive ? "not-allowed" : "pointer",
            opacity: inactive ? 0.6 : 1,
          }}
          disabled={inactive}
          title={cell.note ? cell.note : "Click to edit"}
        >
          {Number(cell.value ?? 0)}
          {cell.note ? (
            <span
              style={{
                display: "inline-block",
                marginLeft: 4,
                color: VALENCE_COLORS.mood,
                fontSize: "0.8rem",
              }}
            >
              ●
            </span>
          ) : null}
        </button>
        {isSaving && (
          <span
            style={{
              position: "absolute",
              bottom: 4,
              right: 6,
              fontSize: "0.65rem",
              color: "#9ba3af",
            }}
          >
            Saving…
          </span>
        )}
        {isEditing && (
          <div
            style={{
              position: "absolute",
              zIndex: 5,
              top: "50%",
              left: "50%",
              transform: "translate(-50%, -50%)",
              backgroundColor: "#111218",
              border: "1px solid #2f3338",
              borderRadius: 8,
              padding: "0.75rem",
              minWidth: 180,
              boxShadow: "0 12px 40px rgba(0,0,0,0.35)",
              display: "grid",
              gap: "0.5rem",
            }}
          >
            <div style={{ fontWeight: 600, fontSize: "0.95rem" }}>
              {row.name} – {day}
            </div>
            <label style={{ display: "grid", gap: "0.3rem", textAlign: "left" }}>
              <span style={{ ...styles.textMuted, fontSize: "0.8rem" }}>Value</span>
              <input
                type="number"
                min={0}
                max={99}
                value={draftValue}
                onChange={(e) => setDraftValue(Number(e.target.value))}
                style={{ ...styles.input, width: "100%" }}
              />
            </label>
            <label style={{ display: "grid", gap: "0.3rem", textAlign: "left" }}>
              <span style={{ ...styles.textMuted, fontSize: "0.8rem" }}>Note</span>
              <textarea
                value={draftNote}
                onChange={(e) => setDraftNote(e.target.value)}
                rows={3}
                maxLength={100}
                style={{ ...styles.input, width: "100%", resize: "vertical" }}
              />
            </label>
            <div style={{ display: "flex", gap: "0.5rem", justifyContent: "flex-end" }}>
              <button
                type="button"
                style={{ ...styles.buttonSecondary, padding: "0.4rem 0.75rem" }}
                onClick={handleCloseEditor}
              >
                Cancel
              </button>
              <button
                type="button"
                style={{ ...styles.button, padding: "0.4rem 0.75rem" }}
                onClick={handleSaveCell}
              >
                Save
              </button>
            </div>
          </div>
        )}
      </td>
    );
  };

  const renderRow = (row: CalendarRow) => {
    const sum = days.reduce(
      (acc, day) => acc + Number(row.cells[day]?.value ?? 0),
      0
    );
    const hits = days.filter((day) => {
      const cell = row.cells[day];
      return row.goal > 0 && Number(cell?.value ?? 0) >= row.goal;
    }).length;

    return (
      <tr key={row.name}>
        <th
          style={{
            position: "sticky",
            left: 0,
            background: "#13141a",
            borderRight: "1px solid #2f3338",
            padding: "0.6rem",
            textAlign: "left",
            fontWeight: 600,
            minWidth: 180,
            zIndex: 3,
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <span
              style={{
                color: row.activity_type === "neutral" ? "#8da5b8" : getValenceColor(row.activity_type),
                fontSize: "1rem",
              }}
            >
              {row.activity_type === "positive"
                ? "✓"
                : row.activity_type === "negative"
                ? "✗"
                : "−"}
            </span>
            <div style={{ display: "grid" }}>
              <span>{row.name}</span>
              <span style={{ ...styles.textMuted, fontSize: "0.75rem" }}>
                {row.category || "Uncategorized"}
              </span>
            </div>
          </div>
        </th>
        {days.map((day) => renderCell(row, day))}
        <td
          style={{
            position: "sticky",
            right: 0,
            background: "#13141a",
            padding: "0.5rem",
            borderLeft: "1px solid #2f3338",
            fontWeight: 600,
            minWidth: 96,
            zIndex: 2,
          }}
          title="Monthly total / goal hits"
        >
          <div style={{ display: "grid", gap: 4 }}>
            <span>{sum.toFixed(0)}</span>
            <span style={{ ...styles.textMuted, fontSize: "0.75rem" }}>
              {hits} goal hit{hits === 1 ? "" : "s"}
            </span>
          </div>
        </td>
      </tr>
    );
  };

  const headerRow = useMemo(() => {
    return (
      <tr>
        <th
          style={{
            position: "sticky",
            left: 0,
            zIndex: 4,
            background: "#0f1015",
            padding: "0.5rem",
            textAlign: "left",
            borderRight: "1px solid #2f3338",
          }}
        >
          Activity
        </th>
        {days.map((day) => (
          <th
            key={day}
            style={{
              background: "#0f1015",
              position: "sticky",
              top: 0,
              zIndex: 3,
              padding: "0.35rem",
              fontSize: "0.8rem",
              border: "1px solid #2f3338",
            }}
            title={day}
          >
            {dayLabel(day)}
          </th>
        ))}
        <th
          style={{
            position: "sticky",
            right: 0,
            top: 0,
            background: "#0f1015",
            padding: "0.5rem",
            borderLeft: "1px solid #2f3338",
            zIndex: 4,
          }}
        >
          Total
        </th>
      </tr>
    );
  }, [days]);

  if (status === "failed") {
    return (
      <ErrorState
        message={
          calendarState.error?.friendlyMessage ||
          calendarState.error?.message ||
          "Failed to load calendar."
        }
        onRetry={() => dispatch(loadCalendarRange({ startDate, endDate }))}
      />
    );
  }

  return (
    <div style={{ display: "grid", gap: "0.75rem" }}>
      {(status === "loading" || calendarState.status === "loading") && (
        <Loading message="Loading calendar…" inline />
      )}
      <div
        style={{
          border: "1px solid #2f3338",
          borderRadius: 12,
          overflow: "auto",
          position: "relative",
          boxShadow: "0 12px 30px rgba(0,0,0,0.2)",
        }}
      >
        <table
          style={{
            width: "100%",
            borderCollapse: "collapse",
            minWidth: Math.max(720, days.length * 56),
          }}
        >
          <thead>{headerRow}</thead>
          <tbody>{rows.map(renderRow)}</tbody>
        </table>
      </div>
      {rows.length === 0 && status === "succeeded" && (
        <div style={{ ...styles.textMuted }}>No entries for this range.</div>
      )}
    </div>
  );
}
