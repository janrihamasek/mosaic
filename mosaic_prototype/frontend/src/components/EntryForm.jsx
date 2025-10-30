import { useEffect, useMemo } from "react";
import { useDispatch, useSelector } from "react-redux";
import { useForm } from "react-hook-form";
import { styles } from "../styles/common";
import CsvImportButton from "./CsvImportButton";
import { selectAllActivities } from "../store/activitiesSlice";
import { loadEntries, selectEntriesFilters, selectEntriesList } from "../store/entriesSlice";
import { formatError } from "../utils/errors";

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

export default function EntryForm({ onNotify }) {
  const dispatch = useDispatch();
  const activities = useSelector(selectAllActivities);
  const entries = useSelector(selectEntriesList);
  const filters = useSelector(selectEntriesFilters);

  const defaultSingleDate = useMemo(() => toLocalDateString(new Date()), []);
  const defaultMonth = useMemo(() => {
    const now = new Date();
    return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
  }, []);

  const {
    register,
    handleSubmit,
    watch,
    reset,
    getValues,
    trigger,
    formState: { errors, isValid, isSubmitting },
  } = useForm({
    mode: "onChange",
    reValidateMode: "onChange",
    shouldUnregister: true,
    defaultValues: {
      dateMode: "all",
      singleDate: defaultSingleDate,
      month: defaultMonth,
      rangeStart: "",
      rangeEnd: "",
      activity: "all",
      category: "all",
    },
  });

  const dateModeValue = watch("dateMode");
  const rangeStartValue = watch("rangeStart");
  const rangeEndValue = watch("rangeEnd");

  useEffect(() => {
    const { startDate, endDate } = filters;
    const nextValues = {
      dateMode: "all",
      singleDate: defaultSingleDate,
      month: defaultMonth,
      rangeStart: "",
      rangeEnd: "",
      activity: filters.activity ?? "all",
      category: filters.category ?? "all",
    };

    if (startDate || endDate) {
      if (startDate && endDate && startDate === endDate) {
        nextValues.dateMode = "single";
        nextValues.singleDate = startDate;
      } else if (startDate && endDate) {
        const start = new Date(`${startDate}T00:00:00`);
        const end = new Date(`${endDate}T00:00:00`);
        const isSameMonth =
          start.getFullYear() === end.getFullYear() &&
          start.getMonth() === end.getMonth() &&
          start.getDate() === 1 &&
          toLocalDateString(new Date(start.getFullYear(), start.getMonth() + 1, 0)) === endDate;

        if (isSameMonth) {
          nextValues.dateMode = "month";
          nextValues.month = `${start.getFullYear()}-${String(start.getMonth() + 1).padStart(2, "0")}`;
        } else {
          nextValues.dateMode = "range";
          nextValues.rangeStart = startDate;
          nextValues.rangeEnd = endDate;
        }
      } else {
        nextValues.dateMode = "range";
        if (startDate) nextValues.rangeStart = startDate;
        if (endDate) nextValues.rangeEnd = endDate;
      }
    }

    reset(nextValues);
    trigger();
  }, [filters, reset, trigger, defaultSingleDate, defaultMonth]);

  useEffect(() => {
    if (dateModeValue === "range") {
      trigger(["rangeStart", "rangeEnd"]);
    }
  }, [dateModeValue, rangeStartValue, rangeEndValue, trigger]);

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
    const unique = new Set();
    activities.forEach((activity) => {
      const category = activity?.category?.trim();
      if (category) unique.add(category);
    });
    entries.forEach((entry) => {
      const category = entry?.category?.trim();
      if (category) unique.add(category);
    });
    const list = Array.from(unique).sort((a, b) =>
      a.localeCompare(b, undefined, { sensitivity: "base" })
    );
    return [
      { value: "all", label: "All categories" },
      ...list.map((c) => ({ value: c, label: c })),
    ];
  }, [activities, entries]);

  const buildInputStyle = (hasError, overrides) => ({
    ...styles.input,
    border: hasError ? "1px solid #d93025" : styles.input.border,
    ...(overrides || {}),
  });

  const errorTextStyle = { color: "#f28b82", fontSize: 12 };

  const onSubmit = async (formData) => {
    let startDate = null;
    let endDate = null;

    switch (formData.dateMode) {
      case "single":
        startDate = formData.singleDate;
        endDate = formData.singleDate;
        break;
      case "month":
        try {
          const [yearStr, monthStr] = formData.month.split("-");
          const year = Number(yearStr);
          const monthIndex = Number(monthStr);
          const firstDay = new Date(year, monthIndex - 1, 1);
          const lastDay = new Date(year, monthIndex, 0);
          startDate = toLocalDateString(firstDay);
          endDate = toLocalDateString(lastDay);
        } catch {
          onNotify?.("Invalid month selection.", "error");
          return;
        }
        break;
      case "range":
        startDate = formData.rangeStart || null;
        endDate = formData.rangeEnd || null;
        break;
      default:
        break;
    }

    try {
      await dispatch(
        loadEntries({
          startDate,
          endDate,
          activity: formData.activity,
          category: formData.category,
        })
      ).unwrap();
    } catch (err) {
      onNotify?.(`Failed to apply filters: ${formatError(err)}`, "error");
    }
  };

  return (
    <form
      onSubmit={handleSubmit(onSubmit)}
      style={{ ...styles.form, display: "flex", flexWrap: "wrap", gap: 12 }}
    >
      <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
        <select
          {...register("dateMode", {
            required: "Select a date mode.",
          })}
          style={buildInputStyle(!!errors.dateMode, { minWidth: 160 })}
        >
          {dateModes.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
        {errors.dateMode && <span style={errorTextStyle}>{errors.dateMode.message}</span>}
      </div>

      {dateModeValue === "single" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          <input
            type="date"
            {...register("singleDate", {
              required: "Please select a date.",
              maxLength: {
                value: 10,
                message: "Date value should be 10 characters.",
              },
            })}
            style={buildInputStyle(!!errors.singleDate)}
          />
          {errors.singleDate && <span style={errorTextStyle}>{errors.singleDate.message}</span>}
        </div>
      )}

      {dateModeValue === "month" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          <input
            type="month"
            {...register("month", {
              required: "Please select a month.",
              maxLength: {
                value: 7,
                message: "Month value should be YYYY-MM.",
              },
              validate: {
                format: (value) =>
                  /^\d{4}-(0[1-9]|1[0-2])$/.test(value) || "Invalid month format.",
                yearRange: (value) => {
                  if (!value) return true;
                  const [yearStr] = value.split("-");
                  const year = Number(yearStr);
                  return (year >= 2000 && year <= 2100) || "Year must be between 2000 and 2100.";
                },
              },
            })}
            style={buildInputStyle(!!errors.month)}
          />
          {errors.month && <span style={errorTextStyle}>{errors.month.message}</span>}
        </div>
      )}

      {dateModeValue === "range" && (
        <div style={{ display: "flex", gap: 8, alignItems: "flex-start" }}>
          <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            <input
              type="date"
              {...register("rangeStart", {
                required: "Select start date.",
                maxLength: {
                  value: 10,
                  message: "Date value should be 10 characters.",
                },
                validate: {
                  beforeEnd: (value) => {
                    const end = getValues("rangeEnd");
                    if (!value || !end) return true;
                    return value <= end || "Range start must be on or before end date.";
                  },
                },
              })}
              style={buildInputStyle(!!errors.rangeStart)}
            />
            {errors.rangeStart && (
              <span style={errorTextStyle}>{errors.rangeStart.message}</span>
            )}
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            <input
              type="date"
              {...register("rangeEnd", {
                required: "Select end date.",
                maxLength: {
                  value: 10,
                  message: "Date value should be 10 characters.",
                },
                validate: {
                  afterStart: (value) => {
                    const start = getValues("rangeStart");
                    if (!value || !start) return true;
                    return start <= value || "Range end must be on or after start date.";
                  },
                },
              })}
              style={buildInputStyle(!!errors.rangeEnd)}
            />
            {errors.rangeEnd && <span style={errorTextStyle}>{errors.rangeEnd.message}</span>}
          </div>
        </div>
      )}

      <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
        <select
          {...register("activity", {
            required: "Select an activity option.",
            maxLength: {
              value: 120,
              message: "Activity value is too long.",
            },
          })}
          style={buildInputStyle(!!errors.activity, { minWidth: 200 })}
        >
          {activityOptions.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
        {errors.activity && <span style={errorTextStyle}>{errors.activity.message}</span>}
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
        <select
          {...register("category", {
            required: "Select a category option.",
            maxLength: {
              value: 120,
              message: "Category value is too long.",
            },
          })}
          style={buildInputStyle(!!errors.category, { minWidth: 180 })}
        >
          {categoryOptions.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
        {errors.category && <span style={errorTextStyle}>{errors.category.message}</span>}
      </div>

      <button
        type="submit"
        style={{
          ...styles.button,
          opacity: !isValid || isSubmitting ? 0.7 : 1,
          cursor: !isValid || isSubmitting ? "not-allowed" : styles.button.cursor,
        }}
        disabled={!isValid || isSubmitting}
      >
        {isSubmitting ? "Applying…" : "Enter"}
      </button>

      <CsvImportButton onNotify={onNotify} variant="import" />
    </form>
  );
}
