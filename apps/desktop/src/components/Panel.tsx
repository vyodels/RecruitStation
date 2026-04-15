import React from "react";
import type { ReactNode } from "react";

interface PanelProps {
  title?: string;
  eyebrow?: string;
  description?: string;
  actions?: ReactNode;
  children: ReactNode;
  dense?: boolean;
}

export function Panel({ title, eyebrow, description, actions, children, dense }: PanelProps): JSX.Element {
  return (
    <section className={`panel${dense ? " panel--dense" : ""}`}>
      {(title || eyebrow || description || actions) && (
        <header className="panel__header">
          <div>
            {eyebrow ? <div className="panel__eyebrow">{eyebrow}</div> : null}
            {title ? <h2 className="panel__title">{title}</h2> : null}
            {description ? <p className="panel__description">{description}</p> : null}
          </div>
          {actions ? <div className="panel__actions">{actions}</div> : null}
        </header>
      )}
      {children}
    </section>
  );
}
