import React, { useCallback, useEffect } from "react";
import { styles } from "../../styles/common";
import { useCompactLayout } from "../../utils/useBreakpoints";

const noop = () => {};

export default function ModalForm({
  isOpen,
  onClose = noop,
  title,
  children,
  footerContent,
  closeLabel = "Close",
  isDismissDisabled = false,
}) {
  const { isCompact } = useCompactLayout();

  const handleKeyDown = useCallback(
    (event) => {
      if (isDismissDisabled) return;
      if (event.key === "Escape") {
        event.preventDefault();
        onClose();
      }
    },
    [isDismissDisabled, onClose]
  );

  useEffect(() => {
    if (!isOpen || typeof window === "undefined") return undefined;
    window.addEventListener("keydown", handleKeyDown);
    const { body } = window.document;
    const previousOverflow = body.style.overflow;
    body.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
      body.style.overflow = previousOverflow;
    };
  }, [handleKeyDown, isOpen]);

  if (!isOpen) {
    return null;
  }

  return (
    <div
      onClick={(event) => {
        if (event.target === event.currentTarget && !isDismissDisabled) {
          onClose();
        }
      }}
      role="presentation"
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 1200,
        backgroundColor: "rgba(0, 0, 0, 0.6)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: isCompact ? "1rem" : "2rem",
      }}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-label={title}
        style={{
          ...styles.card,
          width: "100%",
          maxWidth: isCompact ? "32rem" : "40rem",
          maxHeight: "90vh",
          overflowY: "auto",
          margin: 0,
          display: "flex",
          flexDirection: "column",
          gap: "1rem",
        }}
      >
        <header style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <h2 style={{ margin: 0 }}>{title}</h2>
          <button
            type="button"
            onClick={onClose}
            style={{
              ...styles.button,
              ...(isCompact ? styles.buttonMobile : {}),
              backgroundColor: "#3a3b3f",
              minWidth: isCompact ? "auto" : "6rem",
            }}
            disabled={isDismissDisabled}
          >
            {closeLabel}
          </button>
        </header>
        <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>{children}</div>
        {footerContent && <footer>{footerContent}</footer>}
      </div>
    </div>
  );
}
