import React, { useRef, useState } from "react";
import { importEntriesCsv } from "../api";
import { styles } from "../styles/common";

export default function CsvImportButton({ onImported, onNotify, variant = "default" }) {
  const inputRef = useRef(null);
  const [loading, setLoading] = useState(false);

  const handleClick = () => {
    inputRef.current?.click();
  };

  const handleChange = async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setLoading(true);
    try {
      const result = await importEntriesCsv(file);
      const summary = result?.summary;
      const created = summary?.created ?? 0;
      const updated = summary?.updated ?? 0;
      const skipped = summary?.skipped ?? 0;
      onNotify?.(
        `CSV import completed (${created} created, ${updated} updated, ${skipped} skipped)`,
        "success"
      );
      await onImported?.();
    } catch (err) {
      onNotify?.(`CSV import failed: ${err.message}`, "error");
    } finally {
      setLoading(false);
      if (inputRef.current) {
        inputRef.current.value = "";
      }
    }
  };

  return (
    <>
      <input
        type="file"
        accept=".csv,text/csv"
        ref={inputRef}
        onChange={handleChange}
        style={{ display: "none" }}
      />
      <button
        type="button"
        onClick={handleClick}
        style={{
          ...styles.button,
          opacity: loading ? 0.7 : 1,
          backgroundColor: variant === "import" ? "#29442f" : styles.button.backgroundColor,
          borderColor: variant === "import" ? "#29442f" : styles.button.backgroundColor,
        }}
        disabled={loading}
      >
        {loading ? "Importing..." : "Import CSV"}
      </button>
    </>
  );
}
