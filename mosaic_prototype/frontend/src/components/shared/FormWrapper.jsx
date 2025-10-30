import React from "react";
import { styles } from "../../styles/common";
import { useCompactLayout } from "../../utils/useBreakpoints";

/**
 * Provides a consistent card-style container and action row for form usage.
 * Optional cancel handling is included to centralize shared layout logic.
 */
export default function FormWrapper({
  title,
  onSubmit,
  children,
  isSubmitting = false,
  submitLabel = "Submit",
  onCancel,
  cancelLabel = "Cancel",
  description,
  footer,
  ...formProps
}) {
  const { isCompact } = useCompactLayout();

  const actionRowStyle = {
    display: "flex",
    flexDirection: isCompact ? "column" : "row",
    justifyContent: isCompact ? "stretch" : "flex-end",
    alignItems: isCompact ? "stretch" : "center",
    gap: "0.75rem",
    marginTop: "1rem",
  };

  const buttonBase = {
    ...styles.button,
    ...(isCompact ? styles.buttonMobile : {}),
    minWidth: isCompact ? "100%" : "9rem",
  };

  return (
    <form
      onSubmit={onSubmit}
      style={{
        ...styles.card,
        margin: 0,
        display: "flex",
        flexDirection: "column",
        gap: "0.75rem",
      }}
      {...formProps}
    >
      {title && (
        <header>
          <h2 style={{ margin: 0 }}>{title}</h2>
          {description && (
            <p style={{ ...styles.textMuted, fontSize: "0.875rem", marginTop: "0.25rem" }}>{description}</p>
          )}
        </header>
      )}

      <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>{children}</div>

      {footer}

      <div style={actionRowStyle}>
        {onCancel && (
          <button
            type="button"
            onClick={onCancel}
            style={{
              ...buttonBase,
              backgroundColor: "#3a3b3f",
            }}
            disabled={isSubmitting}
          >
            {cancelLabel}
          </button>
        )}
        <button
          type="submit"
          style={{
            ...buttonBase,
            opacity: isSubmitting ? 0.75 : 1,
            cursor: isSubmitting ? "not-allowed" : styles.button.cursor,
          }}
          disabled={isSubmitting}
        >
          {submitLabel}
        </button>
      </div>
    </form>
  );
}
