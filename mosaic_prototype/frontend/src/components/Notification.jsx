import React from "react";
import { styles } from "../styles/common";
import { useCompactLayout } from "../utils/useBreakpoints";

export default function Notification({ message, visible, type = "success" }) {
  if (!visible || !message) return null;
  const { isCompact } = useCompactLayout();

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
    ...(isCompact ? { width: "100%", minWidth: "auto" } : {}),
  };

  const icon = iconMap[type] || iconMap.success;

  return (
    <div style={toastStyle}>
      {icon} {message}
    </div>
  );
}
