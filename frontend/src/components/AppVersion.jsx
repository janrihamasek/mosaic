import React from "react";
import { styles } from "../styles/common";
import { BUILD_VERSION } from "../buildVersion";
import { updatePWA } from "../registerServiceWorker";

const containerStyle = {
  ...styles.textMuted,
  fontSize: "0.7rem",
  display: "flex",
  alignItems: "center",
  gap: "0.4rem",
  marginTop: "0.35rem",
};

const buttonStyle = {
  border: "1px solid rgba(255,255,255,0.2)",
  background: "transparent",
  color: "#9ba3af",
  borderRadius: "0.25rem",
  padding: "0.15rem 0.55rem",
  fontSize: "0.65rem",
  cursor: "pointer",
};

export default function AppVersion() {
  return (
    <div style={containerStyle}>
      <span>Client version: {BUILD_VERSION}</span>
      <button type="button" style={buttonStyle} onClick={() => void updatePWA()}>
        Check for update
      </button>
    </div>
  );
}
