import React from "react";
import type { ButtonHTMLAttributes } from "react";

import Loading from "../Loading";
import { styles } from "../../styles/common";
import { useCompactLayout } from "../../utils/useBreakpoints";
import type { FormWrapperProps } from "../../types/props";

/**
 * Provides a consistent card-style container and action row for form usage.
 * Optional cancel handling is included to centralize shared layout logic.
 */
const FormWrapper: React.FC<FormWrapperProps> = ({
  title,
  onSubmit,
  children,
  isLoading = false,
  isSubmitting = false,
  isSubmitDisabled = false,
  submitLabel = "Submit",
  onCancel,
  cancelLabel = "Cancel",
  description,
  footer,
  submitButtonProps,
  cancelButtonProps,
  isCollapsed = false,
  ...formProps
}) => {
  const { isCompact } = useCompactLayout();
  const isBusy = isSubmitting || isLoading;
  const resolvedSubmitButtonProps: ButtonHTMLAttributes<HTMLButtonElement> =
    submitButtonProps ?? ({} as ButtonHTMLAttributes<HTMLButtonElement>);
  const resolvedCancelButtonProps: ButtonHTMLAttributes<HTMLButtonElement> =
    cancelButtonProps ?? ({} as ButtonHTMLAttributes<HTMLButtonElement>);
  const { style: cancelStyle, disabled: cancelDisabled, ...restCancelButtonProps } = resolvedCancelButtonProps;
  const { style: submitStyle, ...restSubmitButtonProps } = resolvedSubmitButtonProps;

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
      aria-busy={isBusy}
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

      {!isCollapsed && (
        <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>{children}</div>
      )}

      {!isCollapsed && footer}

      {!isCollapsed && (
        <div style={actionRowStyle}>
          {isLoading && <Loading inline />}
          {onCancel && (
            <button
              type="button"
              onClick={onCancel}
              style={{
                ...buttonBase,
                backgroundColor: "#3a3b3f",
                opacity: isBusy || cancelDisabled ? 0.7 : 1,
                cursor: isBusy || cancelDisabled ? "not-allowed" : styles.button.cursor,
                ...(cancelStyle ?? {}),
              }}
              disabled={isBusy || cancelDisabled}
              {...restCancelButtonProps}
            >
              {cancelLabel}
            </button>
          )}
          <button
            type="submit"
            style={{
              ...buttonBase,
              opacity: isBusy ? 0.75 : 1,
              cursor: isBusy || isSubmitDisabled ? "not-allowed" : styles.button.cursor,
              ...(submitStyle ?? {}),
            }}
            disabled={isBusy || isSubmitDisabled}
            {...restSubmitButtonProps}
          >
            {submitLabel}
          </button>
        </div>
      )}
    </form>
  );
};

export default FormWrapper;
