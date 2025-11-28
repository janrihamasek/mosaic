import React from "react";
import { styles } from "../styles/common";

interface EmptyStateProps {
  message: string;
  action?: {
    label: string;
    onClick: () => void;
  };
  hint?: string;
}

export const EmptyState: React.FC<EmptyStateProps> = ({ message, action, hint }) => {
  return (
    <div
      style={{
        ...styles.card,
        border: "1px solid #3a3b3f",
        backgroundColor: "#2a2b2f",
        color: "#9ba3af",
        display: "flex",
        flexDirection: "column",
        gap: "0.75rem",
        alignItems: "center",
        textAlign: "center",
        padding: "2rem 1.5rem",
      }}
    >
      <span style={{ fontSize: "1rem", color: "#e6e6e6" }}>{message}</span>
      {hint && (
        <span style={{ fontSize: "0.875rem", color: "#9ba3af", marginTop: "0.25rem" }}>
          {hint}
        </span>
      )}
      {action && (
        <button
          type="button"
          onClick={action.onClick}
          style={{
            ...styles.button,
            marginTop: "0.5rem",
            backgroundColor: "#3a7bd5",
          }}
        >
          {action.label}
        </button>
      )}
    </div>
  );
};

export default EmptyState;
