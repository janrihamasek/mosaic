export const MOBILE_WIDTH = "30rem";
export const TABLET_WIDTH = "48rem";
export const DESKTOP_MIN_WIDTH = "48.0625rem";

export const BREAKPOINTS = {
  mobile: {
    min: "0rem",
    max: MOBILE_WIDTH,
  },
  tablet: {
    min: "30.0625rem",
    max: TABLET_WIDTH,
  },
  desktop: {
    min: DESKTOP_MIN_WIDTH,
  },
};

const getMin = (breakpoint) => BREAKPOINTS[breakpoint]?.min;
const getMax = (breakpoint) => BREAKPOINTS[breakpoint]?.max;

export const mediaQuery = {
  upTo: (breakpoint) => {
    const max = getMax(breakpoint);
    return max ? `@media (max-width: ${max})` : null;
  },
  from: (breakpoint) => {
    const min = getMin(breakpoint);
    return min ? `@media (min-width: ${min})` : null;
  },
  between: (lower, upper) => {
    const min = getMin(lower);
    const max = getMax(upper);
    return min && max ? `@media (min-width: ${min}) and (max-width: ${max})` : null;
  },
};

const mobileMedia = mediaQuery.upTo("mobile");
const tabletMedia = mediaQuery.between("tablet", "tablet");
const desktopMedia = mediaQuery.from("desktop");

export const media = {
  mobile: mobileMedia,
  tablet: tabletMedia,
  desktop: desktopMedia,
};

const withMedia = (query, value) => (query ? { [query]: value } : {});

const baseContainer = {
  maxWidth: "60rem",
  width: "100%",
  margin: "1.5rem auto",
  fontFamily: "Segoe UI, sans-serif",
  backgroundColor: "#1e1f22",
  color: "#e6e6e6",
  padding: "1.5rem",
  borderRadius: "0.625rem",
  boxShadow: "0 0 0.75rem rgba(0,0,0,0.6)",
};

const baseInput = {
  padding: "0.45rem 0.75rem",
  marginRight: "0.5rem",
  borderRadius: "0.25rem",
  border: "1px solid #555",
  backgroundColor: "#2a2b2f",
  color: "#e6e6e6",
  width: "100%",
  maxWidth: "22rem",
};

const baseButton = {
  padding: "0.5rem 0.9rem",
  backgroundColor: "#3a7bd5",
  color: "#fff",
  border: "none",
  borderRadius: "0.25rem",
  cursor: "pointer",
  transition: "background 0.3s ease",
  fontSize: "0.95rem",
  lineHeight: 1.4,
};

const baseTable = {
  width: "100%",
  borderCollapse: "collapse",
  marginTop: "0.75rem",
  backgroundColor: "#25262a",
  overflow: "hidden",
  borderRadius: "0.5rem",
};

const baseCard = {
  border: "1px solid #333",
  backgroundColor: "#2a2b2f",
  padding: "1.25rem",
  borderRadius: "0.5rem",
  margin: "0.75rem 0",
  boxShadow: "0 0 0.65rem rgba(0,0,0,0.45)",
};

const baseForm = {
  marginBottom: "1.25rem",
  display: "flex",
  flexWrap: "wrap",
  gap: "0.75rem",
};

const baseText = {
  fontSize: "1rem",
  lineHeight: 1.6,
  color: "#e6e6e6",
};

export const responsiveStyles = {
  container: {
    tablet: {
      padding: "1.25rem",
      margin: "1rem auto",
    },
    mobile: {
      padding: "1rem",
      margin: "0.75rem auto",
      borderRadius: "0.5rem",
    },
  },
  card: {
    tablet: {
      padding: "1.1rem",
    },
    mobile: {
      padding: "0.85rem",
      margin: "0.5rem 0",
    },
  },
  form: {
    tablet: {
      gap: "0.75rem",
    },
    mobile: {
      flexDirection: "column",
    },
  },
  button: {
    tablet: {
      alignSelf: "flex-start",
    },
    mobile: {
      width: "100%",
      padding: "0.65rem 1rem",
    },
  },
  table: {
    tablet: {
      fontSize: "0.95rem",
    },
    mobile: {
      width: "100%",
      overflowX: "auto",
      display: "block",
    },
  },
  input: {
    tablet: {
      maxWidth: "100%",
    },
    mobile: {
      width: "100%",
      marginRight: 0,
      marginBottom: "0.5rem",
    },
  },
  text: {
    tablet: {
      fontSize: "1rem",
    },
    mobile: {
      fontSize: "0.9375rem",
      lineHeight: 1.5,
    },
  },
};

export const styles = {
  container: {
    ...baseContainer,
    ...withMedia(media.tablet, responsiveStyles.container.tablet),
    ...withMedia(media.mobile, responsiveStyles.container.mobile),
  },
  // Mobile-first container override for compact layouts.
  containerMobile: {
    maxWidth: "100%",
    ...responsiveStyles.container.mobile,
  },
  // Tablet-friendly container spacing.
  containerTablet: {
    maxWidth: "52rem",
    margin: "1.25rem auto",
    padding: "1.25rem",
  },
  input: {
    ...baseInput,
    ...withMedia(media.tablet, responsiveStyles.input.tablet),
  },
  // Compact input variant suited for stacked mobile forms.
  inputMobile: {
    ...responsiveStyles.input.mobile,
  },
  button: {
    ...baseButton,
    ...withMedia(media.tablet, responsiveStyles.button.tablet),
    ...withMedia(media.mobile, responsiveStyles.button.mobile),
  },
  // Primary button spacing tuned for handheld layouts.
  buttonMobile: {
    ...responsiveStyles.button.mobile,
  },
  buttonHover: {
    backgroundColor: "#5592e6",
  },
  table: {
    ...baseTable,
    ...withMedia(media.tablet, responsiveStyles.table.tablet),
    ...withMedia(media.mobile, responsiveStyles.table.mobile),
  },
  // Scrollable table wrapper for narrow screens.
  tableMobile: {
    ...responsiveStyles.table.mobile,
  },
  tableCompact: {
    width: "100%",
    borderCollapse: "collapse",
    marginTop: "0.5rem",
  },
  text: {
    ...baseText,
    ...withMedia(media.tablet, responsiveStyles.text.tablet),
    ...withMedia(media.mobile, responsiveStyles.text.mobile),
  },
  // Muted text for helper copy on small devices.
  textMuted: {
    fontSize: "0.875rem",
    color: "#9ba3af",
  },
  // Heading adjustments to scale gracefully on handhelds.
  textHeading: {
    fontSize: "1.5rem",
    lineHeight: 1.3,
    ...withMedia(media.mobile, { fontSize: "1.25rem" }),
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
    ...baseForm,
    ...withMedia(media.tablet, responsiveStyles.form.tablet),
    ...withMedia(media.mobile, responsiveStyles.form.mobile),
  },
  // Vertical form layout for compact viewports.
  formStacked: {
    display: "flex",
    flexDirection: "column",
    gap: "0.75rem",
  },
  card: {
    ...baseCard,
    ...withMedia(media.tablet, responsiveStyles.card.tablet),
    ...withMedia(media.mobile, responsiveStyles.card.mobile),
  },
  // Card layout optimised for handheld usage.
  cardMobile: {
    ...responsiveStyles.card.mobile,
  },
  tableCellActions: {
    width: "40%",
    display: "flex",
    gap: "0.5rem",
    justifyContent: "flex-end",
    ...withMedia(media.mobile, {
      width: "100%",
      justifyContent: "flex-start",
    }),
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
    marginBottom: "0.75rem",
    ...withMedia(media.mobile, {
      flexDirection: "column",
      alignItems: "flex-start",
      gap: "0.5rem",
    }),
  },
  flexRow: {
    display: "flex",
    alignItems: "center",
    gap: "0.625rem",
    ...withMedia(media.mobile, {
      flexWrap: "wrap",
    }),
  },
  tabBar: {
    display: "flex",
    borderBottom: "1px solid #444",
    marginBottom: "1.25rem",
    ...withMedia(media.mobile, {
      overflowX: "auto",
      gap: "0.5rem",
    }),
  },
  tab: {
    padding: "0.65rem 0.95rem",
    cursor: "pointer",
    borderBottom: "3px solid transparent",
    textTransform: "uppercase",
    color: "#ccc",
    transition: "all 0.3s ease",
    whiteSpace: "nowrap",
  },
  tabActive: {
    borderBottom: "3px solid #3a7bd5",
    fontWeight: "bold",
    color: "#fff",
  },
  cardContainer: {
    border: "1px solid #444",
    borderRadius: "0.5rem",
    padding: "1.25rem",
    backgroundColor: "#1a1a1a",
    color: "#ddd",
    marginBottom: "1.25rem",
    boxShadow: "0 0 0.65rem rgba(224, 199, 199, 0.3)",
    ...withMedia(media.mobile, {
      padding: "1rem",
    }),
  },
  toastContainer: {
    position: "fixed",
    top: "1.25rem",
    right: "1.25rem",
    zIndex: 1000,
    ...withMedia(media.mobile, {
      left: "50%",
      right: "auto",
      transform: "translateX(-50%)",
    }),
  },
  toast: {
    minWidth: "15rem",
    padding: "0.65rem 0.9rem",
    borderRadius: "0.375rem",
    backgroundColor: "#2a2b2f",
    boxShadow: "0 0.25rem 0.75rem rgba(0,0,0,0.4)",
    ...withMedia(media.mobile, {
      width: "calc(100vw - 2.5rem)",
      minWidth: "auto",
    }),
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
    marginTop: "0.75rem",
  },
};
