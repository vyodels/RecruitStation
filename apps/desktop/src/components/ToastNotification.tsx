import React from "react";
import { useI18n } from "../lib/i18n";

interface ToastNotificationProps {
  title: React.ReactNode;
  message: React.ReactNode;
  tone?: "critical" | "warning" | "neutral";
  onClose(): void;
}

export function ToastNotification({ title, message, tone = "critical", onClose }: ToastNotificationProps): JSX.Element {
  const { copy } = useI18n();

  return (
    <div className="toast-notification" data-tone={tone} role="alert" aria-live="assertive">
      <div className="toast-notification__content">
        <strong className="toast-notification__title">{title}</strong>
        <div className="toast-notification__message">{message}</div>
      </div>
      <button
        type="button"
        className="toast-notification__close"
        onClick={onClose}
        aria-label={copy("Close notification", "关闭通知")}
      >
        x
      </button>
    </div>
  );
}
