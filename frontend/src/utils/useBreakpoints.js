import { useEffect, useMemo, useState } from "react";
import { mediaQuery } from "../styles/common";

const normalizeQuery = (query) => {
  if (!query) return null;
  const normalized = query.replace(/^@media\s*/i, "").trim();
  if (!normalized) {
    return null;
  }
  if (normalized.startsWith("screen")) {
    return normalized;
  }
  return normalized.startsWith("(") ? `screen and ${normalized}` : normalized;
};

const useMediaMatch = (query) => {
  const normalizedQuery = useMemo(() => normalizeQuery(query), [query]);
  const [matches, setMatches] = useState(() => {
    if (typeof window === "undefined" || !normalizedQuery) return false;
    return window.matchMedia(normalizedQuery).matches;
  });

  useEffect(() => {
    if (typeof window === "undefined" || !normalizedQuery) return undefined;
    const mediaList = window.matchMedia(normalizedQuery);
    const handler = (event) => setMatches(event.matches);
    setMatches(mediaList.matches);
    if (typeof mediaList.addEventListener === "function") {
      mediaList.addEventListener("change", handler);
      return () => mediaList.removeEventListener("change", handler);
    }
    mediaList.addListener(handler);
    return () => mediaList.removeListener(handler);
  }, [normalizedQuery]);

  return matches;
};

export const useBreakpoints = () => {
  const isMobile = useMediaMatch(mediaQuery.upTo("mobile"));
  const isTablet = useMediaMatch(mediaQuery.between("tablet", "tablet"));
  const isDesktop = useMediaMatch(mediaQuery.from("desktop"));
  return { isMobile, isTablet, isDesktop };
};

export const useCompactLayout = () => {
  const { isMobile, isTablet, isDesktop } = useBreakpoints();
  return {
    isMobile,
    isTablet,
    isDesktop,
    isCompact: isMobile || isTablet,
  };
};
