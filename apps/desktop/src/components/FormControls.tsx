import React from "react";
import type {
  ButtonHTMLAttributes,
  InputHTMLAttributes,
  ReactNode,
  SelectHTMLAttributes,
  TextareaHTMLAttributes,
} from "react";

function classNames(...values: Array<string | false | null | undefined>): string {
  return values.filter(Boolean).join(" ");
}

interface FormFieldProps {
  label?: ReactNode;
  children: ReactNode;
  className?: string;
}

export function FormField({ label, children, className }: FormFieldProps): JSX.Element {
  return (
    <label className={classNames("form-field", className)}>
      {label ? <span className="form-field__label">{label}</span> : null}
      {children}
    </label>
  );
}

export const FormInput = React.forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(
  ({ className, ...props }, ref) => <input ref={ref} className={classNames("form-input", className)} {...props} />,
);
FormInput.displayName = "FormInput";

export const FormSelect = React.forwardRef<HTMLSelectElement, SelectHTMLAttributes<HTMLSelectElement>>(
  ({ className, ...props }, ref) => <select ref={ref} className={classNames("form-select", className)} {...props} />,
);
FormSelect.displayName = "FormSelect";

export const FormTextarea = React.forwardRef<HTMLTextAreaElement, TextareaHTMLAttributes<HTMLTextAreaElement>>(
  ({ className, ...props }, ref) => <textarea ref={ref} className={classNames("form-textarea", className)} {...props} />,
);
FormTextarea.displayName = "FormTextarea";

export const FormCheckbox = React.forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(
  ({ className, type = "checkbox", ...props }, ref) => (
    <input ref={ref} type={type} className={classNames("form-checkbox", className)} {...props} />
  ),
);
FormCheckbox.displayName = "FormCheckbox";

interface FormButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "default" | "primary" | "danger";
}

export function FormButton({
  className,
  variant = "default",
  type = "button",
  ...props
}: FormButtonProps): JSX.Element {
  return (
    <button
      type={type}
      className={classNames(
        "form-button",
        variant === "primary" && "form-button--primary",
        variant === "danger" && "form-button--danger",
        className,
      )}
      {...props}
    />
  );
}
