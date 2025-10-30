import React from "react";
import { useDispatch, useSelector } from "react-redux";
import { styles } from "../styles/common";
import { formatError } from "../utils/errors";
import { deleteEntry, loadEntries, selectEntriesList, selectEntriesState } from "../store/entriesSlice";
import Loading from "./Loading";
import ErrorState from "./ErrorState";

export default function EntryTable({ onNotify }) {
  const dispatch = useDispatch();
  const entries = useSelector(selectEntriesList);
  const { deletingId, status, error } = useSelector(selectEntriesState);
  const loading = status === "loading";
  const refreshing = loading && entries.length > 0;

  const handleDelete = async (id) => {
    if (deletingId !== null) return;
    try {
      await dispatch(deleteEntry(id)).unwrap();
      onNotify?.("Entry was deleted", "success");
    } catch (err) {
      onNotify?.(`Failed to delete entry: ${formatError(err)}`, "error");
    }
  };

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

  if (loading && entries.length === 0) {
    return <Loading message="Loading entries…" />;
  }

  return (
    <div>
      {refreshing && <Loading message="Refreshing entries…" inline />}

      <table style={styles.table}>
        <thead>
          <tr style={styles.tableHeader}>
            <th>Date</th>
            <th>Activity</th>
            <th>Category</th>
            <th>Goal</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {entries.map((entry, idx) => {
            const id = entry.id ?? idx;
            const goalValue = Number(entry.goal ?? 0);
            return (
              <tr key={id} style={styles.tableRow}>
                <td>{entry.date}</td>
                <td title={entry.category ? `Category: ${entry.category}` : "Category: N/A"}>{entry.activity}</td>
                <td>{entry.category || "N/A"}</td>
                <td>{goalValue ? goalValue.toFixed(2) : "0.00"}</td>
                <td style={{ width: "12%", textAlign: "right" }}>
                  <button
                    onClick={() => handleDelete(id)}
                    style={{ ...styles.button, backgroundColor: "#8b1e3f", opacity: deletingId === id ? 0.6 : 1 }}
                    disabled={deletingId === id}
                  >
                    {deletingId === id ? "Deleting..." : "Delete"}
                  </button>
                </td>
              </tr>
            );
          })}
          {!loading && entries.length === 0 && (
            <tr>
              <td colSpan={5} style={{ padding: "12px", color: "#888" }}>
                No entries to display.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
