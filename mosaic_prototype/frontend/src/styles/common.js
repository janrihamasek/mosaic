export const styles = {
  container: {
    maxWidth: "900px",
    margin: "20px auto",
    fontFamily: "Segoe UI, sans-serif",
    backgroundColor: "#1e1f22",
    color: "#e6e6e6",
    padding: "20px",
    borderRadius: "10px",
    boxShadow: "0 0 12px rgba(0,0,0,0.6)",
  },
  input: {
    padding: "6px 8px",
    marginRight: "8px",
    borderRadius: "4px",
    border: "1px solid #555",
    backgroundColor: "#2a2b2f",
    color: "#e6e6e6",
  },
  button: {
    padding: "6px 12px",
    backgroundColor: "#3a7bd5",
    color: "#fff",
    border: "none",
    borderRadius: "4px",
    cursor: "pointer",
    transition: "background 0.3s ease",
  },
  buttonHover: {
    backgroundColor: "#5592e6",
  },
  table: {
    width: "100%",
    borderCollapse: "collapse",
    marginTop: "10px",
    backgroundColor: "#25262a",
  },
  tableHeader: {
    backgroundColor: "#2f3136",
    textAlign: "left",
    color: "#e6e6e6",
  },
  tableRow: {
    borderBottom: "1px solid #333",
  },
  form: {
    marginBottom: "20px",
  },
  card: {
    border: "1px solid #333",
    backgroundColor: "#2a2b2f",
    padding: 16,
    borderRadius: 8,
    margin: "12px 0",
  },
  tableCellActions: {
    width: "35%",
    display: "flex",
    gap: 8,
    justifyContent: "flex-end",
  },
  highlightRow: {
    backgroundColor: "#29442f",
  },
  successMessage: {
    color: "#7cd992",
  },
  rowBetween: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 12,
  },
  flexRow: {
    display: "flex",
    alignItems: "center",
    gap: "10px",
  },
  tabBar: {
    display: "flex",
    borderBottom: "1px solid #444",
    marginBottom: "20px",
  },
  tab: {
    padding: "10px 15px",
    cursor: "pointer",
    borderBottom: "3px solid transparent",
    textTransform: "uppercase",
    color: "#ccc",
    transition: "all 0.3s ease",
  },
  tabActive: {
    borderBottom: "3px solid #3a7bd5",
    fontWeight: "bold",
    color: "#fff",
  },
  cardContainer: {
    border: "1px solid #444",
    borderRadius: "8px",
    padding: "16px",
    backgroundColor: "#1a1a1a",
    color: "#ddd",
    marginBottom: "20px",
    boxShadow: "0 0 10px rgba(224, 199, 199, 0.3)",
  },
  toastContainer: {
    position: "fixed",
    top: "20px",
    right: "20px",
    zIndex: 1000,
  },
  toast: {
    minWidth: "240px",
    padding: "10px 14px",
    borderRadius: "6px",
    backgroundColor: "#2a2b2f",
    boxShadow: "0 4px 12px rgba(0,0,0,0.4)",
  },
  toastSuccess: {
    color: "#7cd992",
  },
  toastError: {
    color: "#f28b82",
  },
  toastInfo: {
    color: "#8ab4f8",
  },
  loadingText: {
    color: "#9ba3af",
    fontStyle: "italic",
    marginTop: "10px",
  },
};
