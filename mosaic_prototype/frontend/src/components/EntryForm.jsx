import React, { useMemo, useState } from "react";
import { styles } from "../styles/common";
import CsvImportButton from "./CsvImportButton";

const toLocalDateString = (dateObj) => {
  const tzOffset = dateObj.getTimezoneOffset();
  const adjusted = new Date(dateObj.getTime() - tzOffset * 60000);
  return adjusted.toISOString().slice(0, 10);
};

const dateModes = [
  { value: "all", label: "All time" },
  { value: "single", label: "Single day" },
  { value: "month", label: "Month" },
  { value: "range", label: "Range" },
];

export default function EntryForm({
  activities = [],
  categories = [],
  onApplyFilters,
  onNotify,
  onImported,
}) {
  const [dateMode, setDateMode] = useState("all");
  const [singleDate, setSingleDate] = useState(() => toLocalDateString(new Date()));
  const [month, setMonth] = useState(() => {
    const now = new Date();
    return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
  });
  const [rangeStart, setRangeStart] = useState("");
  const [rangeEnd, setRangeEnd] = useState("");
  const [selectedActivity, setSelectedActivity] = useState("all");
  const [selectedCategory, setSelectedCategory] = useState("all");

  const activityOptions = useMemo(() => {
    const list = [...activities]
      .sort((a, b) =>
        (a.name || "").localeCompare(b.name || "", undefined, { sensitivity: "base" })
      )
      .map((a) => ({
        value: a.name,
        label: a.category ? `${a.category} - ${a.name}` : a.name,
      }));
    return [{ value: "all", label: "All activities" }, ...list];
  }, [activities]);

  const categoryOptions = useMemo(() => {
    const unique = new Set(
      categories
        .map((c) => c?.trim())
        .filter((c) => c && c.length > 0)
    );
    const list = Array.from(unique).sort((a, b) =>
      a.localeCompare(b, undefined, { sensitivity: "base" })
    );
    return [
      { value: "all", label: "All categories" },
      ...list.map((c) => ({ value: c, label: c })),
    ];
  }, [categories]);

  const handleSubmit = (e) => {
    e.preventDefault();
    let startDate = null;
    let endDate = null;

    switch (dateMode) {
      case "single":
        if (!singleDate) {
          onNotify?.("Please select a date.", "error");
          return;
        }
        startDate = singleDate;
        endDate = singleDate;
        break;
      case "month":
        if (!month) {
          onNotify?.("Please select a month.", "error");
          return;
        }
        try {
          const [year, monthPart] = month.split("-").map(Number);
          if (!year || !monthPart) throw new Error();
          const firstDay = new Date(year, monthPart - 1, 1);
          const lastDay = new Date(year, monthPart, 0);
          startDate = toLocalDateString(firstDay);
          endDate = toLocalDateString(lastDay);
        } catch {
          onNotify?.("Invalid month selection.", "error");
          return;
        }
        break;
      case "range":
        if (!rangeStart || !rangeEnd) {
          onNotify?.("Please select start and end dates.", "error");
          return;
        }
        if (rangeStart > rangeEnd) {
          onNotify?.("Range start must be before range end.", "error");
          return;
        }
        startDate = rangeStart;
        endDate = rangeEnd;
        break;
      default:
        break;
    }

    onApplyFilters?.({
      startDate,
      endDate,
      activity: selectedActivity,
      category: selectedCategory,
    });
  };

  return (
    <form onSubmit={handleSubmit} style={{ ...styles.form, display: "flex", flexWrap: "wrap", gap: 12 }}>
      <select
        value={dateMode}
        onChange={(e) => setDateMode(e.target.value)}
        style={{ ...styles.input, minWidth: 160 }}
      >
        {dateModes.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>

      {dateMode === "single" && (
        <input
          type="date"
          value={singleDate}
          onChange={(e) => setSingleDate(e.target.value)}
          style={styles.input}
        />
      )}

      {dateMode === "month" && (
        <input
          type="month"
          value={month}
          onChange={(e) => setMonth(e.target.value)}
          style={styles.input}
        />
      )}

      {dateMode === "range" && (
        <div style={{ display: "flex", gap: 8 }}>
          <input
            type="date"
            value={rangeStart}
            onChange={(e) => setRangeStart(e.target.value)}
            style={styles.input}
          />
          <input
            type="date"
            value={rangeEnd}
            onChange={(e) => setRangeEnd(e.target.value)}
            style={styles.input}
          />
        </div>
      )}

      <select
        value={selectedActivity}
        onChange={(e) => setSelectedActivity(e.target.value)}
        style={{ ...styles.input, minWidth: 200 }}
      >
        {activityOptions.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>

      <select
        value={selectedCategory}
        onChange={(e) => setSelectedCategory(e.target.value)}
        style={{ ...styles.input, minWidth: 180 }}
      >
        {categoryOptions.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>

      <button type="submit" style={styles.button}>
        Enter
      </button>

      <CsvImportButton onImported={onImported} onNotify={onNotify} />
    </form>
  );
}
