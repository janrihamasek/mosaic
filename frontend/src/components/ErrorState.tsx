import React, { useEffect } from "react";
import { styles } from "../styles/common";
import { ensureStatusAnimations } from "../utils/animations";
import type { ErrorStateProps } from "../types/props";

export const ErrorState: React.FC<ErrorStateProps> = ({
  message = "Something went wrong.",
  onRetry,
  actionLabel = "Try again",
}) => {
  useEffect(() => {
    ensureStatusAnimations();
  }, []);

  return (
    <div
      role="alert"
      style={{
        ...styles.card,
        border: "1px solid #5c1f24",
        backgroundColor: "#3b1f24",
        color: "#f28b82",
        display: "flex",
        flexDirection: "column",
        gap: 8,
        animation: "mosaic-fade-in 220ms ease-in-out",
      }}
    >
      <span>⚠️ {message}</span>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          style={{
            ...styles.button,
            alignSelf: "flex-start",
            backgroundColor: "#8b1e3f",
          }}
        >
          {actionLabel}
        </button>
      )}
    </div>
  );
};

export default ErrorState;
