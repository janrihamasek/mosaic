import type {
  ButtonHTMLAttributes,
  FormEvent,
  FormHTMLAttributes,
  ReactNode,
} from "react";

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

export interface FormWrapperProps
  extends Omit<FormHTMLAttributes<HTMLFormElement>, "onSubmit"> {
  title?: ReactNode;
  onSubmit?: (event: FormEvent<HTMLFormElement>) => void;
  children: ReactNode;
  isLoading?: boolean;
  isSubmitting?: boolean;
  isSubmitDisabled?: boolean;
  submitLabel?: string;
  onCancel?: () => void;
  cancelLabel?: string;
  description?: ReactNode;
  footer?: ReactNode;
  submitButtonProps?: ButtonHTMLAttributes<HTMLButtonElement>;
  cancelButtonProps?: ButtonHTMLAttributes<HTMLButtonElement>;
  isCollapsed?: boolean;
}

export interface DataTableColumn {
  key?: string;
  label?: string;
  title?: string;
  width?: string | number;
  render?: (row: any) => ReactNode;
}

export interface DataTableErrorLike {
  message?: string;
  friendlyMessage?: string;
}

export interface DataTableProps {
  columns: DataTableColumn[];
  data: any[];
  isLoading?: boolean;
  error?: string | DataTableErrorLike | null;
  emptyMessage?: ReactNode;
  loadingMessage?: string;
  errorLabel?: string;
  onRowClick?: (row: any) => void;
}

export {};
