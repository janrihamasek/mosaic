import React, { useEffect, useMemo, useState } from "react";
import { useSelector } from "react-redux";

import { styles } from "../styles/common";
import { useCompactLayout } from "../utils/useBreakpoints";
import AdminUser from "./AdminUser";
import AdminSettings from "./AdminSettings";
import AdminNightMotion from "./AdminNightMotion";
import AdminLogs from "./AdminLogs";
import HealthPanel from "./HealthPanel";
import { selectAuth } from "../store/authSlice";

const SECTIONS = [
  { id: "user", label: "User", Component: AdminUser },
  { id: "settings", label: "Settings", Component: AdminSettings },
  { id: "health", label: "Health", Component: HealthPanel },
  { id: "logs", label: "Logs", Component: AdminLogs },
  { id: "nightMotion", label: "NightMotion", Component: AdminNightMotion },
];

export default function Admin({ onNotify }) {
  const auth = useSelector(selectAuth);
  const { isCompact } = useCompactLayout();
  const sections = useMemo(
    () => (auth.isAdmin ? SECTIONS : SECTIONS.filter((section) => section.id === "user")),
    [auth.isAdmin]
  );
  const [activeSection, setActiveSection] = useState(sections[0]?.id ?? "user");

  useEffect(() => {
    if (!sections.find((section) => section.id === activeSection)) {
      setActiveSection(sections[0]?.id ?? "user");
    }
  }, [sections, activeSection]);

  const layoutStyle = useMemo(
    () => ({
      display: "flex",
      flexDirection: isCompact ? "column" : "row",
      alignItems: "stretch",
      gap: "1.25rem",
      width: "100%",
    }),
    [isCompact]
  );

  const menuContainerStyle = useMemo(
    () => ({
      flex: isCompact ? "0 0 auto" : "0 0 14rem",
      display: "flex",
      flexDirection: isCompact ? "row" : "column",
      gap: isCompact ? "0.5rem" : "0.65rem",
      backgroundColor: isCompact ? "transparent" : "#232428",
      border: isCompact ? "none" : "1px solid #2f3034",
      borderRadius: "0.5rem",
      padding: isCompact ? 0 : "0.75rem",
      overflowX: isCompact ? "auto" : "visible",
    }),
    [isCompact]
  );

  const menuItemStyle = useMemo(
    () => ({
      ...styles.tab,
      display: "flex",
      justifyContent: "center",
      alignItems: "center",
      width: isCompact ? "auto" : "100%",
      backgroundColor: "transparent",
      border: isCompact ? "none" : "1px solid transparent",
      borderBottom: isCompact ? "3px solid transparent" : "1px solid transparent",
      borderRadius: isCompact ? "0.4rem" : "0.45rem",
      textTransform: "none",
      fontWeight: 500,
      textAlign: "center",
      color: "#ccc",
    }),
    [isCompact]
  );

  const menuItemActiveStyle = useMemo(
    () =>
      isCompact
        ? styles.tabActive
        : {
            backgroundColor: "#2b2c30",
            borderColor: "#3a7bd5",
            color: "#fff",
            fontWeight: 600,
          },
    [isCompact]
  );

  const contentStyle = useMemo(
    () => ({
      flex: "1 1 auto",
      minWidth: 0,
      display: "flex",
      flexDirection: "column",
      gap: "1.25rem",
    }),
    []
  );

  const ActiveComponent =
    sections.find((section) => section.id === activeSection)?.Component || AdminUser;

  return (
    <div style={layoutStyle}>
      <nav style={menuContainerStyle} aria-label="Admin menu">
        {sections.map((section) => (
          <button
            key={section.id}
            type="button"
            onClick={() => setActiveSection(section.id)}
            style={{
              ...menuItemStyle,
              ...(activeSection === section.id ? menuItemActiveStyle : {}),
            }}
          >
            {section.label}
          </button>
        ))}
      </nav>
      <div style={contentStyle}>
        <ActiveComponent onNotify={onNotify} />
      </div>
    </div>
  );
}
