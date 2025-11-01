import React, {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { useDispatch, useSelector } from "react-redux";
import { useForm } from "react-hook-form";

import { styles } from "../styles/common";
import { useCompactLayout } from "../utils/useBreakpoints";
import FormWrapper from "./shared/FormWrapper";
import { getStreamProxyUrl } from "../api";
import {
  selectNightMotionState,
  setError,
  setField,
  setStatus,
  startStream,
  stopStream,
  type NightMotionStatus,
} from "../store/nightMotionSlice";
import type { AppDispatch } from "../store";

type NotifyVariant = "success" | "error" | "info";

interface NightMotionProps {
  onNotify?: (message: string, variant?: NotifyVariant) => void;
}

interface NightMotionFormValues {
  username: string;
  password: string;
  streamUrl: string;
}

const statusColors: Record<NightMotionStatus, string> = {
  idle: "#888888",
  connecting: "#d0b000",
  playing: "#2ecc71",
  error: "#e74c3c",
};

const statusLabels: Record<NightMotionStatus, string> = {
  idle: "Idle",
  connecting: "Connecting…",
  playing: "Live",
  error: "Error",
};

const STORAGE_KEY = "nightMotionConfig";

const formFieldStyles = {
  display: "flex",
  flexDirection: "column" as const,
  gap: "0.35rem",
};

const passwordToggleStyle = {
  ...styles.button,
  padding: "0.4rem 0.6rem",
  fontSize: "0.8rem",
  backgroundColor: "#444",
};

const videoWrapperBase = {
  ...styles.card,
  display: "flex",
  flexDirection: "column" as const,
  gap: "1rem",
  minHeight: "20rem",
  flex: "1 1 24rem",
  background: "linear-gradient(145deg, #1f2228 0%, #252830 100%)",
};

export default function NightMotion({ onNotify }: NightMotionProps) {
  const dispatch = useDispatch<AppDispatch>();
  const { username, password, streamUrl, status, error } = useSelector(selectNightMotionState);
  const [showPassword, setShowPassword] = useState(false);
  const [statusVisible, setStatusVisible] = useState(true);
  const { isCompact } = useCompactLayout();
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const hasHydratedConfig = useRef(false);

  const {
    register,
    handleSubmit,
    reset,
    formState: { isSubmitting },
  } = useForm<NightMotionFormValues>({
    defaultValues: { username, password, streamUrl },
  });

  const layoutStyle = useMemo(
    () => ({
      display: "flex",
      flexDirection: isCompact ? "column" : "row",
      alignItems: "stretch",
      gap: isCompact ? "1rem" : "1.5rem",
      width: "100%",
    }),
    [isCompact]
  );

  const videoWrapperStyle = useMemo(
    () => ({
      ...videoWrapperBase,
      minHeight: isCompact ? "18rem" : videoWrapperBase.minHeight,
    }),
    [isCompact]
  );

  const videoStyle = useMemo(
    () => ({
      width: "100%",
      height: isCompact ? "16rem" : "18rem",
      backgroundColor: "#000",
      borderRadius: "0.5rem",
      border: "1px solid #333",
      objectFit: "cover" as const,
      transition: "opacity 0.35s ease, transform 0.35s ease",
      opacity: status === "playing" ? 1 : 0.85,
    }),
    [isCompact, status]
  );

  const statusIndicatorStyle = useMemo(
    () => ({
      display: "inline-flex",
      alignItems: "center",
      gap: "0.6rem",
      fontWeight: 600,
      color: statusColors[status],
      transition: "opacity 0.3s ease, transform 0.3s ease",
      opacity: statusVisible ? 1 : 0,
      transform: statusVisible ? "translateY(0px)" : "translateY(-6px)",
    }),
    [status, statusVisible]
  );

  const statusDotStyle = useMemo(
    () => ({
      width: "0.75rem",
      height: "0.75rem",
      borderRadius: "999px",
      backgroundColor: statusColors[status],
      boxShadow: `0 0 0.4rem ${statusColors[status]}55`,
    }),
    [status]
  );

  const startDisabled = status === "connecting" || status === "playing";
  const stopDisabled = status === "idle";
  const submitLabel = useMemo(() => {
    if (isSubmitting) return "Starting…";
    if (status === "connecting") return "Connecting…";
    if (status === "playing") return "Streaming";
    return "Start";
  }, [isSubmitting, status]);

  const notify = useCallback(
    (message: string, variant: NotifyVariant = "info") => {
      if (message) {
        onNotify?.(message, variant);
      }
    },
    [onNotify]
  );

  const clearVideoSource = useCallback(() => {
    const node = videoRef.current;
    if (!node) return;
    node.pause();
    node.removeAttribute("src");
    node.load();
  }, []);

  const handleStop = useCallback(() => {
    if (stopDisabled) {
      return;
    }
    clearVideoSource();
    dispatch(stopStream());
  }, [clearVideoSource, dispatch, stopDisabled]);

  useEffect(
    () => () => {
      clearVideoSource();
      dispatch(stopStream());
    },
    [clearVideoSource, dispatch]
  );

  useEffect(() => {
    setStatusVisible(false);
    const timeout = window.setTimeout(() => setStatusVisible(true), 40);
    return () => window.clearTimeout(timeout);
  }, [status]);

  useEffect(() => {
    if (typeof window === "undefined" || hasHydratedConfig.current) {
      return;
    }
    try {
      const storedRaw = window.localStorage.getItem(STORAGE_KEY);
      if (!storedRaw) {
        hasHydratedConfig.current = true;
        return;
      }
      const parsed = JSON.parse(storedRaw) as Partial<NightMotionFormValues>;
      const safeValues: NightMotionFormValues = {
        username: typeof parsed.username === "string" ? parsed.username : "",
        password: typeof parsed.password === "string" ? parsed.password : "",
        streamUrl: typeof parsed.streamUrl === "string" ? parsed.streamUrl : "",
      };
      dispatch(setField({ field: "username", value: safeValues.username }));
      dispatch(setField({ field: "password", value: safeValues.password }));
      dispatch(setField({ field: "streamUrl", value: safeValues.streamUrl }));
      reset(safeValues);
    } catch {
      // Ignore malformed payloads — users can re-enter credentials.
      window.localStorage.removeItem(STORAGE_KEY);
    } finally {
      hasHydratedConfig.current = true;
    }
  }, [dispatch, reset]);

  useEffect(() => {
    const node = videoRef.current;
    if (!node) return undefined;
    const handleVideoError = () => {
      dispatch(setStatus("error"));
      dispatch(setError("Stream nelze navázat"));
      notify("Stream nelze navázat", "error");
    };
    node.addEventListener("error", handleVideoError);
    return () => {
      node.removeEventListener("error", handleVideoError);
    };
  }, [dispatch, notify]);

  const registerTextField = useCallback(
    (field: keyof NightMotionFormValues) =>
      register(field, {
        onChange: (event) => {
          dispatch(setField({ field, value: event.target.value }));
          if (status === "error") {
            dispatch(setError(null));
            dispatch(setStatus("idle"));
          }
        },
      }),
    [dispatch, register, status]
  );

  const onSubmit = handleSubmit(async (values) => {
    const payload: NightMotionFormValues = {
      username: values.username.trim(),
      password: values.password,
      streamUrl: values.streamUrl.trim(),
    };

    if (!payload.username || !payload.password || !payload.streamUrl) {
      dispatch(setError("Vyplňte všechna pole"));
      dispatch(setStatus("error"));
      notify("Vyplňte všechna pole", "error");
      return;
    }

    try {
      // Validate URL format eagerly to surface issues before attempting playback.
      // eslint-disable-next-line no-new
      new URL(payload.streamUrl);
    } catch {
      dispatch(setError("Neplatná URL adresa"));
      dispatch(setStatus("error"));
      notify("Stream nelze navázat", "error");
      return;
    }

    dispatch(setField({ field: "username", value: payload.username }));
    dispatch(setField({ field: "password", value: payload.password }));
    dispatch(setField({ field: "streamUrl", value: payload.streamUrl }));
    dispatch(setError(null));

    if (typeof window !== "undefined") {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(payload));
    }
    notify("Nastavení uloženo", "success");

    const streamSrc = getStreamProxyUrl(payload.streamUrl, payload.username, payload.password);
    if (videoRef.current) {
      videoRef.current.src = streamSrc;
      videoRef.current.load();
    }

    try {
      await dispatch(startStream());
    } catch {
      dispatch(setStatus("error"));
      dispatch(setError("Stream nelze navázat"));
      notify("Stream nelze navázat", "error");
    }
  });

  return (
    <div style={layoutStyle}>
      <div style={{ flex: "1 1 22rem" }}>
        <FormWrapper
          title="NightMotion"
          onSubmit={onSubmit}
          isSubmitting={isSubmitting}
          isSubmitDisabled={startDisabled}
          submitLabel={submitLabel}
          onCancel={handleStop}
          cancelLabel="Stop"
          submitButtonProps={{ "data-testid": "nightmotion-start" }}
          cancelButtonProps={{ disabled: stopDisabled, "data-testid": "nightmotion-stop" }}
        >
          <div style={{ display: "flex", flexDirection: "column", gap: "0.9rem" }}>
            <label style={formFieldStyles}>
              <span>Uživatelské jméno</span>
              <input
                type="text"
                placeholder="username"
                {...registerTextField("username")}
                style={{ ...styles.input, width: "100%" }}
                autoComplete="username"
                data-testid="nightmotion-username"
              />
            </label>
            <label style={formFieldStyles}>
              <span>Heslo</span>
              <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
                <input
                  type={showPassword ? "text" : "password"}
                  placeholder="password"
                  {...registerTextField("password")}
                  style={{ ...styles.input, width: "100%" }}
                  autoComplete="current-password"
                  data-testid="nightmotion-password"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((prev) => !prev)}
                  style={{
                    ...passwordToggleStyle,
                    backgroundColor: showPassword ? "#3a7bd5" : "#444",
                  }}
                  aria-label={showPassword ? "Hide password" : "Show password"}
                >
                  {showPassword ? "Hide" : "Show"}
                </button>
              </div>
            </label>
            <label style={formFieldStyles}>
              <span>Stream URL</span>
              <input
                type="url"
                placeholder="rtsp://"
                {...registerTextField("streamUrl")}
                style={{ ...styles.input, width: "100%" }}
                autoComplete="off"
                data-testid="nightmotion-stream"
              />
            </label>
          </div>
        </FormWrapper>
      </div>

      <div style={videoWrapperStyle}>
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: "0.5rem",
          }}
        >
          <div style={statusIndicatorStyle} aria-live="polite" data-testid="nightmotion-status">
            <span style={statusDotStyle} />
            <span>{statusLabels[status]}</span>
          </div>
          {error && (
            <span style={{ color: statusColors.error, fontSize: "0.85rem" }} data-testid="nightmotion-error">
              {error}
            </span>
          )}
        </div>

        <video
          ref={videoRef}
          controls
          style={videoStyle}
          data-testid="nightmotion-video"
        >
          <track kind="captions" />
        </video>

        <div
          style={{
            fontSize: "0.85rem",
            color: "#b0b0b8",
            lineHeight: 1.5,
          }}
        >
          <p style={{ margin: 0 }}>
            Stream se spustí s krátkým zpožděním, aby bylo možné navázat šifrované spojení.
            Pokud se přehrávání nespustí, zkontrolujte přístupové údaje nebo adresu streamu.
          </p>
        </div>
      </div>
    </div>
  );
}
