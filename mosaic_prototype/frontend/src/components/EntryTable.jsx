import React, { useCallback, useMemo } from "react";
import { useDispatch, useSelector } from "react-redux";
import { styles } from "../styles/common";
import { formatError } from "../utils/errors";
import { deleteEntry, loadEntries, selectEntriesList, selectEntriesState } from "../store/entriesSlice";
import Loading from "./Loading";
import ErrorState from "./ErrorState";
import DataTable from "./shared/DataTable";

export default function EntryTable({ onNotify }) {
  const dispatch = useDispatch();
  const entries = useSelector(selectEntriesList);
  const { deletingId, status, error } = useSelector(selectEntriesState);
  const loading = status === "loading";
  const refreshing = loading && entries.length > 0;

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

  const actionCellStyle = {
    display: "flex",
    gap: "0.5rem",
    justifyContent: "flex-end",
    flexWrap: "wrap",
  };

  const tableData = useMemo(
    () =>
      entries.map((entry, index) => ({
        ...entry,
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
        width: "30%",
        render: (entry) => (
          <span title={entry.category ? `Category: ${entry.category}` : "Category: N/A"}>
            {entry.activity}
          </span>
        ),
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
        width: "15%",
        render: (entry) => {
          const goalValue = Number(entry.goal ?? 0);
          return goalValue ? goalValue.toFixed(2) : "0.00";
        },
      },
      {
        key: "actions",
        label: "Actions",
        width: "20%",
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
    [deletingId, handleDelete]
  );

  if (status === "failed") {
    const message = error?.friendlyMessage || error?.message || "Failed to load entries.";
    return (
      <ErrorState
        message={message}
        onRetry={() => dispatch(loadEntries())}
        actionLabel="Retry load"
      />
    );
  }

  const isInitialLoading = loading && entries.length === 0;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
      {refreshing && <Loading message="Refreshing entries…" inline />}
      <DataTable
        columns={columns}
        data={tableData}
        isLoading={isInitialLoading}
        loadingMessage={<Loading message="Loading entries…" />}
        emptyMessage="No entries to display."
      />
    </div>
  );
}
