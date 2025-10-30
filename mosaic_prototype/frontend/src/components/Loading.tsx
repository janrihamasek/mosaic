import React, { useEffect } from "react";
import { styles } from "../styles/common";
import { ensureStatusAnimations } from "../utils/animations";
import type { LoadingProps } from "../types/props";

const baseContainerStyle = {
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  gap: 10,
  padding: "16px 0",
};

const Loading: React.FC<LoadingProps> = ({ message = "Loading…", inline = false }) => {
  useEffect(() => {
    ensureStatusAnimations();
  }, []);

  const containerStyle = inline
    ? { ...baseContainerStyle, justifyContent: "flex-start" }
    : baseContainerStyle;

  return (
    <div style={{ ...containerStyle, animation: "mosaic-fade-in 220ms ease-in-out" }}>
      <span
        aria-hidden="true"
        style={{
          width: 16,
          height: 16,
          borderRadius: "50%",
          border: "2px solid #5592e6",
          borderTopColor: "transparent",
          animation: "mosaic-spin 900ms linear infinite",
        }}
      />
      <span style={{ ...styles.loadingText, margin: 0 }}>{message}</span>
    </div>
  );
};

export default Loading;
