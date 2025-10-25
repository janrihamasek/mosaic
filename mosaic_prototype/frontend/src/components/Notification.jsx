import React from "react";
import { styles } from "../styles/common";

export default function Notification({ message, visible }) {
  if (!visible) return null;
  return (
    <div style={{ ...styles.successMessage, textAlign: "right" }}>
      ✅ {message}
    </div>
  );
}
