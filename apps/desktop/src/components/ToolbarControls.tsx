import React from "react";
import type { ButtonHTMLAttributes, InputHTMLAttributes, ReactNode, SelectHTMLAttributes } from "react";

function classNames(...values: Array<string | false | null | undefined>): string {
  return values.filter(Boolean).join(" ");
}

interface ToolbarFieldProps {
  label?: ReactNode;
  children: ReactNode;
  className?: string;
}

export function ToolbarField({ label, children, className }: ToolbarFieldProps): JSX.Element {
  return (
    <label className={classNames("toolbar-field", className)}>
      {label ? <span className="toolbar-field__label">{label}</span> : null}
      {children}
    </label>
  );
}

export function ToolbarInput({ className, ...props }: InputHTMLAttributes<HTMLInputElement>): JSX.Element {
  return <input className={classNames("toolbar-input", className)} {...props} />;
}

export function ToolbarSelect({ className, ...props }: SelectHTMLAttributes<HTMLSelectElement>): JSX.Element {
  return <select className={classNames("toolbar-select", className)} {...props} />;
}

interface ToolbarButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "default" | "primary";
  icon?: ReactNode;
}

export function ToolbarButton({
  children,
  className,
  icon,
  type = "button",
  variant = "default",
  ...props
}: ToolbarButtonProps): JSX.Element {
  return (
    <button
      type={type}
      className={classNames("toolbar-button", variant === "primary" && "toolbar-button--primary", className)}
      {...props}
    >
      {icon}
      {children}
    </button>
  );
}

interface ToolbarRefreshButtonProps extends Omit<ToolbarButtonProps, "children" | "icon" | "variant"> {
  refreshing?: boolean;
  label: string;
  refreshingLabel: string;
}

export function ToolbarRefreshButton({
  disabled,
  refreshing = false,
  label,
  refreshingLabel,
  ...props
}: ToolbarRefreshButtonProps): JSX.Element {
  return (
    <ToolbarButton
      {...props}
      variant="primary"
      disabled={disabled || refreshing}
      icon={<span className="toolbar-button__icon toolbar-button__icon--refresh" aria-hidden="true" />}
    >
      {refreshing ? refreshingLabel : label}
    </ToolbarButton>
  );
}
