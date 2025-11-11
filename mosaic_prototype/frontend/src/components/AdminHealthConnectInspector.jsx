import React, { useCallback, useEffect, useMemo, useState } from "react";
import { useDispatch, useSelector } from "react-redux";

import { styles } from "../styles/common";
import { loadWearableSummary, selectWearableInspectorState } from "../store/adminSlice";

const inspectorCard = {
  ...styles.card,
  backgroundColor: "#101828",
  border: "1px solid rgba(255,255,255,0.06)",
  padding: "1rem",
};

const labelStyle = {
  color: "#94a3b8",
  fontSize: "0.75rem",
  letterSpacing: "0.08em",
  textTransform: "uppercase",
};

const fieldStyle = {
  display: "flex",
  flexDirection: "column",
  gap: "0.25rem",
  marginBottom: "0.5rem",
};

export default function AdminHealthConnectInspector() {
  const dispatch = useDispatch();
  const { status, summary, raw, error } = useSelector(selectWearableInspectorState);
  const [filters, setFilters] = useState({ type: "all", date: new Date().toISOString().slice(0, 10) });

  const loading = status === "loading";
  const failed = status === "failed";

  const handleFetch = useCallback(() => {
    dispatch(loadWearableSummary(filters));
  }, [dispatch, filters]);

  useEffect(() => {
    handleFetch();
  }, [handleFetch]);

  const totals = useMemo(() => {
    if (!summary) return {};
    return {
      accepted: summary.accepted ?? summary.accepted_count ?? 0,
      duplicates: summary.duplicates ?? summary.duplicate_count ?? 0,
      errors: summary.errors ?? [],
      lastRun: summary.last_run ?? summary.timestamp ?? null,
    };
  }, [summary]);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
      <div style={inspectorCard}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div>
            <p style={{ ...labelStyle, marginBottom: "0.25rem" }}>HealthConnect Inspector</p>
            <h2 style={{ margin: 0, fontSize: "1.1rem" }}>Ingestion short summary</h2>
          </div>
          <button
            type="button"
            style={{ ...styles.button, fontSize: "0.9rem", padding: "0.35rem 0.75rem" }}
            onClick={handleFetch}
            disabled={loading}
          >
            Refresh
          </button>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(150px,1fr))", gap: "0.75rem", marginTop: "1rem" }}>
          <div>
            <p style={labelStyle}>Accepted</p>
            <strong style={{ fontSize: "1.5rem" }}>{totals.accepted ?? "—"}</strong>
          </div>
          <div>
            <p style={labelStyle}>Duplicates</p>
            <strong style={{ fontSize: "1.5rem" }}>{totals.duplicates ?? "—"}</strong>
          </div>
          <div>
            <p style={labelStyle}>Errors</p>
            <strong style={{ fontSize: "1.5rem" }}>{(totals.errors?.length ?? 0) || "0"}</strong>
          </div>
          <div>
            <p style={labelStyle}>Last run</p>
            <span style={{ color: "#cbd5f5" }}>{totals.lastRun ? new Date(totals.lastRun).toLocaleString() : "—"}</span>
          </div>
        </div>
        <div style={{ marginTop: "1rem", display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
          <div style={fieldStyle}>
            <label style={labelStyle} htmlFor="inspector-type">
              Type
            </label>
            <select
              id="inspector-type"
              value={filters.type}
              onChange={(evt) => setFilters((prev) => ({ ...prev, type: evt.target.value }))}
              style={{ ...styles.input, marginRight: 0 }}
            >
              <option value="all">All</option>
              <option value="steps">Steps</option>
              <option value="heart_rate">Heart Rate</option>
              <option value="sleep">Sleep</option>
            </select>
          </div>
          <div style={fieldStyle}>
            <label style={labelStyle} htmlFor="inspector-date">
              Date
            </label>
            <input
              id="inspector-date"
              type="date"
              value={filters.date}
              onChange={(evt) => setFilters((prev) => ({ ...prev, date: evt.target.value }))}
              style={{ ...styles.input, marginRight: 0 }}
            />
          </div>
        </div>
      </div>

      {failed && (
        <div style={inspectorCard}>
          <p style={{ margin: 0, color: "#f87171" }}>Failed to load inspector data: {error}</p>
        </div>
      )}

      {loading && (
        <div style={inspectorCard}>
          <p style={{ margin: 0 }}>Loading ingestion diagnostics…</p>
        </div>
      )}

      {!failed && !loading && Array.isArray(raw) && raw.length > 0 && (
        <div style={inspectorCard}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <h3 style={{ margin: 0 }}>Recent Raw Records</h3>
            <span style={{ color: "#94a3b8", fontSize: "0.75rem" }}>
              Showing {raw.length} records
            </span>
          </div>
          <div style={{ marginTop: "0.75rem" }}>
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr>
                  <th style={{ textAlign: "left", padding: "0.25rem", fontSize: "0.7rem", color: "#94a3b8" }}>Type</th>
                  <th style={{ textAlign: "left", padding: "0.25rem", fontSize: "0.7rem", color: "#94a3b8" }}>Status</th>
                  <th style={{ textAlign: "left", padding: "0.25rem", fontSize: "0.7rem", color: "#94a3b8" }}>Collected</th>
                </tr>
              </thead>
              <tbody>
                {raw.slice(0, 8).map((record) => (
                  <tr key={record.id || record.dedupe_key}>
                    <td style={{ padding: "0.35rem 0", borderBottom: "1px solid rgba(148,163,184,0.2)" }}>
                      {record.type || record.payload?.type || "–"}
                    </td>
                    <td style={{ padding: "0.35rem 0", borderBottom: "1px solid rgba(148,163,184,0.2)" }}>
                      {record.status || record.result || "ingested"}
                    </td>
                    <td style={{ padding: "0.35rem 0", borderBottom: "1px solid rgba(148,163,184,0.2)" }}>
                      {record.collected_at_utc
                        ? new Date(record.collected_at_utc).toLocaleString()
                        : new Date(record.received_at_utc).toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
