import React from "react";

interface SkeletonRowProps {
  columns: number;
  height?: number;
}

export const SkeletonRow: React.FC<SkeletonRowProps> = ({ columns, height = 40 }) => {
  const skeletonCellStyle: React.CSSProperties = {
    height: `${height}px`,
    backgroundColor: "#2a2b2f",
    borderRadius: "4px",
    position: "relative",
    overflow: "hidden",
  };

  const shimmerStyle: React.CSSProperties = {
    position: "absolute",
    top: 0,
    left: "-100%",
    height: "100%",
    width: "100%",
    background: "linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.05), transparent)",
    animation: "shimmer 1.5s infinite",
  };

  return (
    <tr>
      {Array.from({ length: columns }).map((_, idx) => (
        <td key={idx} style={{ padding: "0.75rem" }}>
          <div style={skeletonCellStyle}>
            <div style={shimmerStyle} />
          </div>
        </td>
      ))}
    </tr>
  );
};

interface SkeletonTableProps {
  rows?: number;
  columns?: number;
}

export const SkeletonTable: React.FC<SkeletonTableProps> = ({ rows = 3, columns = 5 }) => {
  // Inject shimmer keyframes if not already present
  React.useEffect(() => {
    const styleId = "skeleton-shimmer-keyframes";
    if (!document.getElementById(styleId)) {
      const style = document.createElement("style");
      style.id = styleId;
      style.textContent = `
        @keyframes shimmer {
          0% { left: -100%; }
          100% { left: 100%; }
        }
      `;
      document.head.appendChild(style);
    }
  }, []);

  return (
    <table
      style={{
        width: "100%",
        borderCollapse: "collapse",
        marginTop: "0.75rem",
        backgroundColor: "#25262a",
        overflow: "hidden",
        borderRadius: "0.5rem",
      }}
    >
      <tbody>
        {Array.from({ length: rows }).map((_, idx) => (
          <SkeletonRow key={idx} columns={columns} />
        ))}
      </tbody>
    </table>
  );
};

export default SkeletonTable;
