import React, { useCallback, useMemo } from "react";
import { useDispatch, useSelector } from "react-redux";
import { styles, VALENCE_COLORS, getValenceColor } from "../styles/common";
import { formatError } from "../utils/errors";
import { 
  deleteEntry, 
  loadEntries, 
  selectEntriesList, 
  selectEntriesStatus,
  selectEntriesError,
  selectDeletingEntryId,
  selectEntriesFilters,
} from "../store/entriesSlice";
import type { AppDispatch } from "../store";
import type { Entry } from "../types/api";
import Loading from "./Loading";
import ErrorState from "./ErrorState";
import EmptyState from "./EmptyState";
import SkeletonTable from "./SkeletonTable";
import DataTable from "./shared/DataTable";

interface EntryTableProps {
  onNotify?: (message: string, type: "success" | "error" | "info") => void;
}

interface EntryWithIndex extends Entry {
  _rowIndex: number;
}

export default function EntryTable({ onNotify }: EntryTableProps) {
  const dispatch = useDispatch<AppDispatch>();
  const entries = useSelector(selectEntriesList);
  const status = useSelector(selectEntriesStatus);
  const error = useSelector(selectEntriesError);
  const deletingId = useSelector(selectDeletingEntryId);
  const filters = useSelector(selectEntriesFilters);
  
  const loading = status === "loading";
  const refreshing = loading && entries.length > 0;
  const showEmptyState = !loading && !error && entries.length === 0;
  const handleDelete = useCallback(
    async (id) => {
      if (deletingId !== null) return;
      try {
        await dispatch(deleteEntry(id)).unwrap();
        onNotify?.("Entry was deleted", "success");
      } catch (err) {
        onNotify?.(`Failed to delete entry: ${formatError(err)}`, "error");
      }
    },
    [deletingId, dispatch, onNotify]
  );

  const actionCellStyle = useMemo<React.CSSProperties>(
    () => ({
      display: "flex",
      gap: "0.5rem",
      justifyContent: "flex-end",
      flexWrap: "wrap",
    }),
    []
  );
  
  const resolveRowStyle = useCallback(
    (entry: Entry | EntryWithIndex) => {
      const isMood = entry.activity?.toLowerCase() === "mood";
      if (isMood) return styles.moodRow;
      if (entry.activity_type === "negative") return styles.negativeRow;
      if (entry.activity_type === "neutral") return styles.neutralRow;
      return styles.positiveRow;
    },
    []
  );

  const tableData = useMemo<EntryWithIndex[]>(
    () =>
      entries.map((entry, index): EntryWithIndex => ({
        ...entry,
        activity_type: entry.activity_type || "positive",
        _rowIndex: index,
      })),
    [entries]
  );

  const columns = useMemo(
    () => [
      {
        key: "date",
        label: "Date",
        width: "15%",
        render: (entry) => entry.date,
      },
      {
        key: "activity",
        label: "Activity",
        width: "25%",
        render: (entry) => (
          <span title={entry.category ? `Category: ${entry.category}` : "Category: N/A"}>
            {entry.activity}
          </span>
        ),
      },
      {
        key: "type",
        label: "Type",
        width: "8%",
        render: (entry) => {
          const isMood = entry.activity?.toLowerCase() === "mood";
          const color = isMood ? VALENCE_COLORS.mood : getValenceColor(entry.activity_type);
          return (
            <span style={{ 
              fontSize: "1.2rem",
              color,
              display: "flex",
              justifyContent: "center",
            }}>
              {isMood ? "🌙" : entry.activity_type === "positive" ? "✓" : entry.activity_type === "negative" ? "✗" : "−"}
            </span>
          );
        },
      },
      {
        key: "value",
        label: "Value",
        width: "10%",
        render: (entry) => {
          const value = Number(entry.value);
          if (!Number.isFinite(value)) {
            return "0";
          }
          const displayValue = value % 1 === 0 ? value.toString() : value.toFixed(2);
          const isMood = entry.activity?.toLowerCase() === "mood";
          const color = isMood ? VALENCE_COLORS.mood : getValenceColor(entry.activity_type);
          
          return (
            <span style={{ 
              color, 
              fontWeight: 500,
              padding: "0.25rem 0.5rem",
              borderRadius: "0.25rem",
              backgroundColor: `${color}15`,
            }}>
              {displayValue}
            </span>
          );
        },
      },
      {
        key: "category",
        label: "Category",
        width: "20%",
        render: (entry) => entry.category || "N/A",
      },
      {
        key: "goal",
        label: "Goal",
        width: "12%",
        render: (entry) => {
          const goalValue = Number(entry.goal ?? 0);
          return goalValue ? goalValue.toFixed(2) : "0.00";
        },
      },
      {
        key: "actions",
        label: "Actions",
        width: "15%",
        render: (entry) => {
          const id = entry.id ?? entry._rowIndex;
          const isDeleting = deletingId === id;
          return (
            <div style={actionCellStyle}>
              <button
                onClick={(event) => {
                  event.stopPropagation();
                  handleDelete(id);
                }}
                style={{
                  ...styles.button,
                  backgroundColor: "#8b1e3f",
                  opacity: isDeleting ? 0.6 : 1,
                }}
                disabled={isDeleting}
              >
                {isDeleting ? "Deleting..." : "Delete"}
              </button>
            </div>
          );
        },
      },
    ],
    [actionCellStyle, deletingId, handleDelete]
  );

  if (status === "failed") {
    const message = error?.friendlyMessage || error?.message || "Failed to load entries.";
    return (
      <ErrorState
        message={message}
        onRetry={() => dispatch(loadEntries(filters))}
        actionLabel="Reload"
      />
    );
  }

  const isInitialLoading = loading && entries.length === 0;

  if (isInitialLoading) {
    return (
      <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
        <div style={{ ...styles.textMuted, fontSize: "0.875rem" }}>
          Loading entries...
        </div>
        <SkeletonTable rows={5} columns={6} />
      </div>
    );
  }

  if (showEmptyState) {
    return (
      <EmptyState
        message="No records for selected filter"
      />
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
      {refreshing && <Loading message="Refreshing entries…" inline />}
      <DataTable
        columns={columns}
        data={tableData}
        isLoading={false}
        loadingMessage=""
        emptyMessage=""
        rowStyle={resolveRowStyle}
      />
    </div>
  );
}
