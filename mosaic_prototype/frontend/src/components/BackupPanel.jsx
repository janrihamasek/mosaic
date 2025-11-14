import React, { useCallback, useEffect, useMemo, useState } from "react";
import { useDispatch, useSelector } from "react-redux";

import { styles } from "../styles/common";
import { formatError } from "../utils/errors";
import {
  loadBackupStatus,
  runBackupNow,
  selectBackupState,
  selectLatestBackup,
  toggleBackup,
} from "../store/backupSlice";
import { downloadBackupFile } from "../api";

const intervalOptions = [15, 30, 60, 120, 240];

function formatTimestamp(isoString) {
  if (!isoString) return "Never";
  try {
    const date = new Date(isoString);
    return date.toLocaleString();
  } catch (_err) {
    return isoString;
  }
}

export default function BackupPanel({ onNotify }) {
  const dispatch = useDispatch();
  const backupState = useSelector(selectBackupState);
  const latestBackup = useSelector(selectLatestBackup);
  const [downloading, setDownloading] = useState(false);

  const latestBackupSizeKb = useMemo(() => {
    if (!latestBackup || typeof latestBackup.size_bytes !== "number") {
      return null;
    }
    if (latestBackup.size_bytes === 0) {
      return 0;
    }
    return Math.max(1, Math.round(latestBackup.size_bytes / 1024));
  }, [latestBackup]);

  useEffect(() => {
    if (backupState.status === "idle") {
      dispatch(loadBackupStatus());
    }
  }, [backupState.status, dispatch]);

  const handleToggle = useCallback(async () => {
    try {
      const nextEnabled = !backupState.enabled;
      await dispatch(toggleBackup({ enabled: nextEnabled, intervalMinutes: backupState.intervalMinutes })).unwrap();
      onNotify?.(nextEnabled ? "Automatic backups enabled" : "Automatic backups disabled", "success");
    } catch (error) {
      onNotify?.(`Failed to update backup settings: ${formatError(error)}`, "error");
    }
  }, [backupState.enabled, backupState.intervalMinutes, dispatch, onNotify]);

  const handleIntervalChange = useCallback(
    async (event) => {
      const value = Number(event.target.value);
      if (!Number.isFinite(value)) {
        return;
      }
      try {
        await dispatch(
          toggleBackup({ intervalMinutes: value, enabled: backupState.enabled })
        ).unwrap();
        onNotify?.(`Backup interval set to ${value} minutes`, "success");
      } catch (error) {
        onNotify?.(`Failed to update backup interval: ${formatError(error)}`, "error");
      }
    },
    [backupState.enabled, dispatch, onNotify]
  );

  const handleRunNow = useCallback(async () => {
    try {
      await dispatch(runBackupNow()).unwrap();
      onNotify?.("Backup created successfully", "success");
    } catch (error) {
      onNotify?.(`Backup failed: ${formatError(error)}`, "error");
    }
  }, [dispatch, onNotify]);

  const handleDownload = useCallback(async () => {
    if (!latestBackup) return;
    setDownloading(true);
    try {
      const { blob, filename } = await downloadBackupFile(latestBackup.filename);
      if (typeof window === "undefined") {
        throw new Error("Download is not available in this environment");
      }
      const url = window.URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = filename || latestBackup.filename;
      document.body.appendChild(anchor);
      anchor.click();
      document.body.removeChild(anchor);
      window.URL.revokeObjectURL(url);
      onNotify?.("Backup download started", "success");
    } catch (error) {
      onNotify?.(`Failed to download backup: ${formatError(error)}`, "error");
    } finally {
      setDownloading(false);
    }
  }, [latestBackup, onNotify]);

  const hasBackups = useMemo(() => Array.isArray(backupState.backups) && backupState.backups.length > 0, [backupState.backups]);

  const containerStyle = useMemo(
    () => ({
      border: "1px solid #333",
      backgroundColor: "#232428",
      padding: "1rem",
      borderRadius: "0.5rem",
      display: "flex",
      flexDirection: "column",
      gap: "0.75rem",
    }),
    []
  );

  const buttonRowStyle = useMemo(
    () => ({
      display: "flex",
      flexWrap: "wrap",
      gap: "0.75rem",
    }),
    []
  );

  const infoRowStyle = useMemo(
    () => ({
      display: "flex",
      flexDirection: "column",
      gap: "0.35rem",
      fontSize: "0.95rem",
      color: "#ddd",
    }),
    []
  );

  const intervalChoices = useMemo(() => {
    const choices = new Set(intervalOptions);
    if (Number.isFinite(Number(backupState.intervalMinutes))) {
      choices.add(Number(backupState.intervalMinutes));
    }
    return Array.from(choices).sort((a, b) => a - b);
  }, [backupState.intervalMinutes]);

  return (
    <div style={containerStyle}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "1rem" }}>
        <h3 style={{ margin: 0, fontSize: "1.05rem" }}>Backups</h3>
        <button
          onClick={handleToggle}
          style={{
            ...styles.button,
            backgroundColor: backupState.enabled ? "#2f9e44" : "#3a7bd5",
            opacity: backupState.toggling ? 0.7 : 1,
          }}
          disabled={backupState.toggling}
        >
          {backupState.enabled ? "Disable automatic backups" : "Enable automatic backups"}
        </button>
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", flexWrap: "wrap" }}>
        <label htmlFor="backup-interval" style={{ fontSize: "0.95rem" }}>
          Interval
        </label>
        <select
          id="backup-interval"
          value={backupState.intervalMinutes}
          onChange={handleIntervalChange}
          disabled={backupState.toggling}
          style={{
            padding: "0.4rem 0.6rem",
            backgroundColor: "#2a2b2f",
            color: "#e6e6e6",
            borderRadius: "0.25rem",
            border: "1px solid #555",
          }}
        >
          {intervalChoices.map((minutes) => (
            <option key={minutes} value={minutes}>
              {minutes} minutes
            </option>
          ))}
        </select>
      </div>

      <div style={infoRowStyle}>
        <span>Last run: {formatTimestamp(backupState.lastRun)}</span>
        {hasBackups ? (
          <span>
            Latest backup: {latestBackup.filename}
            {latestBackupSizeKb !== null ? ` (${latestBackupSizeKb} kB)` : ""}
          </span>
        ) : (
          <span>No backups created yet.</span>
        )}
      </div>

      {backupState.error && (
        <div style={{ color: "#ff6b6b", fontSize: "0.9rem" }}>
          {backupState.error}
        </div>
      )}

      <div style={buttonRowStyle}>
        <button
          onClick={handleRunNow}
          style={{
            ...styles.button,
            opacity: backupState.running ? 0.7 : 1,
          }}
          disabled={backupState.running}
        >
          {backupState.running ? "Running backup…" : "Run backup now"}
        </button>
        <button
          onClick={handleDownload}
          style={{
            ...styles.button,
            backgroundColor: "#8a4fff",
            opacity: downloading || !hasBackups ? 0.6 : 1,
          }}
          disabled={!hasBackups || downloading}
        >
          {downloading ? "Preparing download…" : "Download last backup"}
        </button>
      </div>
    </div>
  );
}
