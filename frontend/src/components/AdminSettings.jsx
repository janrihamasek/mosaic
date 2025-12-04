import React, { useCallback, useMemo, useState } from "react";

import BackupPanel from "./BackupPanel";
import ImportExportPanel from "./ImportExportPanel";
import { styles } from "../styles/common";
import { deleteUserData } from "../api";
import { formatError } from "../utils/errors";

export default function AdminSettings({ onNotify }) {
  const [wiping, setWiping] = useState(false);

  const wrapperStyle = useMemo(
    () => ({
      display: "flex",
      flexDirection: "column",
      gap: "1.25rem",
    }),
    []
  );

  const dangerCardStyle = useMemo(
    () => ({
      ...styles.card,
      margin: 0,
      display: "flex",
      flexDirection: "column",
      gap: "0.6rem",
      backgroundColor: "#2a1f1f",
      border: "1px solid #553333",
    }),
    []
  );

  const handleWipeData = useCallback(async () => {
    if (wiping) return;
    const confirmed = window.confirm(
      "This will delete all your entries, activities, and backup settings. Continue?"
    );
    if (!confirmed) return;
    setWiping(true);
    try {
      await deleteUserData();
      onNotify?.("All personal data deleted", "success");
      window.location.reload();
    } catch (error) {
      onNotify?.(`Failed to delete data: ${formatError(error)}`, "error");
    } finally {
      setWiping(false);
    }
  }, [onNotify, wiping]);

  return (
    <div style={wrapperStyle}>
      <BackupPanel onNotify={onNotify} />
      <ImportExportPanel onNotify={onNotify} />
      <section style={dangerCardStyle}>
        <h3 style={{ margin: 0, color: "#f28b82" }}>Delete all data</h3>
        <p style={{ ...styles.textMuted, margin: 0 }}>
          Removes all your entries, activities, and backup preferences. This action cannot be undone and does not delete your account.
        </p>
        <button
          type="button"
          onClick={handleWipeData}
          style={{
            ...styles.button,
            backgroundColor: "#a33f3f",
            ...(wiping ? { opacity: 0.7, cursor: "wait" } : {}),
          }}
          disabled={wiping}
        >
          {wiping ? "Deleting…" : "Delete all data"}
        </button>
      </section>
    </div>
  );
}
