import React, { useEffect, useMemo, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { useNavigate } from "react-router-dom";

import { styles } from "../styles/common";
import {
  deleteAccount,
  selectAuth,
  updateCurrentUserProfile,
} from "../store/authSlice";

const initialState = {
  displayName: "",
  password: "",
  passwordConfirm: "",
};

export default function AdminUser({ onNotify }) {
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const auth = useSelector(selectAuth);

  const [form, setForm] = useState(initialState);
  const [formError, setFormError] = useState("");

  useEffect(() => {
    setForm({
      displayName: auth.displayName || auth.username || "",
      password: "",
      passwordConfirm: "",
    });
    setFormError("");
  }, [auth.displayName, auth.username]);

  const isUpdating = auth.status.profileUpdate === "loading";
  const isDeleting = auth.status.deleteAccount === "loading";

  const hasDisplayNameChanged = useMemo(() => {
    const trimmed = form.displayName.trim();
    return trimmed && trimmed !== (auth.displayName || auth.username || "");
  }, [auth.displayName, auth.username, form.displayName]);

  const handleInputChange = (event) => {
    const { name, value } = event.target;
    setForm((prev) => ({
      ...prev,
      [name]: value,
    }));
    setFormError("");
  };

  const handleSave = async () => {
    const updates = {};
    const trimmedDisplayName = form.displayName.trim();
    if (hasDisplayNameChanged) {
      updates.displayName = trimmedDisplayName;
    }
    if (form.password || form.passwordConfirm) {
      if (form.password !== form.passwordConfirm) {
        setFormError("Hesla se neshodují");
        return;
      }
      if (form.password.length < 8) {
        setFormError("Heslo musí mít alespoň 8 znaků");
        return;
      }
      updates.password = form.password;
    }

    if (!updates.displayName && !updates.password) {
      onNotify?.("Žádné změny k uložení", "info");
      return;
    }

    try {
      await dispatch(updateCurrentUserProfile(updates)).unwrap();
      setForm((prev) => ({
        ...prev,
        password: "",
        passwordConfirm: "",
      }));
      setFormError("");
      onNotify?.("Profil byl aktualizován", "success");
    } catch (error) {
      const message = error?.friendlyMessage || error?.message || "Aktualizace profilu selhala";
      setFormError(message);
      onNotify?.(message, "error");
    }
  };

  const handleDelete = async () => {
    if (isDeleting) return;
    const confirmed = window.confirm(
      "Opravdu chcete trvale odstranit svůj účet a všechny související záznamy? Tuto akci nelze vrátit zpět."
    );
    if (!confirmed) return;
    try {
      await dispatch(deleteAccount()).unwrap();
      onNotify?.("Účet byl odstraněn", "success");
      navigate("/login", { replace: true });
    } catch (error) {
      const message = error?.friendlyMessage || error?.message || "Odstranění účtu selhalo";
      setFormError(message);
      onNotify?.(message, "error");
    }
  };

  const infoItems = [
    { label: "Uživatelské jméno", value: auth.username ?? "—" },
    { label: "Zobrazované jméno", value: auth.displayName ?? "—" },
    { label: "Role", value: auth.isAdmin ? "Administrátor" : "Uživatel" },
  ];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
      <section style={{ ...styles.card, margin: 0, display: "flex", flexDirection: "column", gap: "0.5rem" }}>
        <h3 style={{ margin: 0 }}>Profil</h3>
        {infoItems.map((item) => (
          <div
            key={item.label}
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              gap: "0.5rem",
            }}
          >
            <span style={{ ...styles.textMuted, minWidth: "9rem" }}>{item.label}</span>
            <span>{item.value}</span>
          </div>
        ))}
      </section>

      <section style={{ ...styles.card, margin: 0, display: "flex", flexDirection: "column", gap: "0.75rem" }}>
        <h3 style={{ margin: 0 }}>Úpravy profilu</h3>
        <label style={{ display: "flex", flexDirection: "column", gap: "0.35rem" }}>
          <span>Zobrazované jméno</span>
          <input
            type="text"
            name="displayName"
            value={form.displayName}
            onChange={handleInputChange}
            style={styles.input}
            placeholder="Zobrazované jméno"
            disabled={isUpdating}
          />
        </label>
        <label style={{ display: "flex", flexDirection: "column", gap: "0.35rem" }}>
          <span>Nové heslo</span>
          <input
            type="password"
            name="password"
            value={form.password}
            onChange={handleInputChange}
            style={styles.input}
            placeholder="Zadejte nové heslo"
            disabled={isUpdating}
          />
        </label>
        <label style={{ display: "flex", flexDirection: "column", gap: "0.35rem" }}>
          <span>Potvrzení hesla</span>
          <input
            type="password"
            name="passwordConfirm"
            value={form.passwordConfirm}
            onChange={handleInputChange}
            style={styles.input}
            placeholder="Potvrďte heslo"
            disabled={isUpdating}
          />
        </label>

        {formError && (
          <div style={{ color: "#f28b82", fontSize: "0.9rem" }}>
            {formError}
          </div>
        )}

        <button
          type="button"
          onClick={handleSave}
          style={{
            ...styles.button,
            ...(isUpdating ? { opacity: 0.7, cursor: "wait" } : {}),
          }}
          disabled={isUpdating}
        >
          {isUpdating ? "Ukládám…" : "Uložit změny"}
        </button>
      </section>

      <section style={{ ...styles.card, margin: 0, display: "flex", flexDirection: "column", gap: "0.75rem" }}>
        <h3 style={{ margin: 0, color: "#f28b82" }}>Odstranění účtu</h3>
        <p style={{ ...styles.textMuted, margin: 0 }}>
          Tato akce trvale smaže účet a všechny související aktivity i záznamy.
        </p>
        <button
          type="button"
          onClick={handleDelete}
          style={{
            ...styles.button,
            backgroundColor: "#a33f3f",
            ...(isDeleting ? { opacity: 0.7, cursor: "wait" } : {}),
          }}
          disabled={isDeleting}
        >
          {isDeleting ? "Mažu účet…" : "Trvale odstranit účet"}
        </button>
      </section>
    </div>
  );
}
