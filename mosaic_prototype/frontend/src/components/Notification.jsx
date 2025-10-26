import React from "react";
import { styles } from "../styles/common";

export default function Notification({ message, visible, type = "success" }) {
  if (!visible || !message) return null;

  const variantStyleMap = {
    success: styles.toastSuccess,
    error: styles.toastError,
    info: styles.toastInfo,
  };

  const iconMap = {
    success: "✅",
    error: "⚠️",
    info: "ℹ️",
  };

  const toastStyle = {
    ...styles.toast,
    ...(variantStyleMap[type] || styles.toastSuccess),
  };

  const icon = iconMap[type] || iconMap.success;

  return (
    <div style={toastStyle}>
      {icon} {message}
    </div>
  );
}
