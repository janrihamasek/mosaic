import React, { useMemo } from "react";

import BackupPanel from "./BackupPanel";
import ImportExportPanel from "./ImportExportPanel";

export default function AdminSettings({ onNotify }) {
  const wrapperStyle = useMemo(
    () => ({
      display: "flex",
      flexDirection: "column",
      gap: "1.25rem",
    }),
    []
  );

  return (
    <div style={wrapperStyle}>
      <BackupPanel onNotify={onNotify} />
      <ImportExportPanel onNotify={onNotify} />
    </div>
  );
}
