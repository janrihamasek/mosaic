import React from "react";

import { styles } from "../styles/common";

export default function AdminUser() {
  return (
    <div style={{ ...styles.card, margin: 0 }}>
      <h3 style={{ marginTop: 0 }}>User management</h3>
      <p style={{ ...styles.textMuted, marginBottom: 0 }}>
        This area is reserved for upcoming user administration tools.
      </p>
    </div>
  );
}
