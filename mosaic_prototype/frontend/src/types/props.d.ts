import type { ReactNode } from "react";

export interface LoadingProps {
  message?: string;
  inline?: boolean;
}

export interface ErrorStateProps {
  message?: string;
  onRetry?: () => void;
  actionLabel?: string;
}

export interface ModalFormProps {
  isOpen: boolean;
  onClose?: () => void;
  title: string;
  children?: ReactNode;
  footerContent?: ReactNode;
  closeLabel?: string;
  isDismissDisabled?: boolean;
}

export {};
