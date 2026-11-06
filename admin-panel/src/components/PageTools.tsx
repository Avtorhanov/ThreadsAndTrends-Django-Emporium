import type { ReactNode } from "react";
import { Link } from "react-router";

import { Icon, type IconName } from "./Icon";

/**
 * Действия в строке заголовка экрана (справа от названия): «На сайте», «Удалить», «Добавить»…
 * Одинаковые компактные кнопки во всей панели: на телефоне — только иконка (подпись — aria-label
 * и title), на компьютере — иконка с подписью.
 */
export function PageTools({ children }: { children: ReactNode }) {
  return <div className="page-tools">{children}</div>;
}

type ToolProps = {
  icon: IconName;
  label: string;
  tone?: "danger" | "accent";
  disabled?: boolean;
} & ({ onClick: () => void; href?: never; to?: never } | { href: string; onClick?: never; to?: never } | { to: string; onClick?: never; href?: never });

export function ToolButton({ icon, label, tone, disabled, ...action }: ToolProps) {
  const className = tone ? `tool-button tool-button-${tone}` : "tool-button";
  const content = (
    <>
      <Icon name={icon} size={18} />
      <span className="tool-button-label">{label}</span>
    </>
  );
  if (action.href !== undefined) {
    return (
      <a className={className} href={action.href} target="_blank" rel="noreferrer" aria-label={label} title={label}>
        {content}
      </a>
    );
  }
  if (action.to !== undefined) {
    return (
      <Link className={className} to={action.to} aria-label={label} title={label}>
        {content}
      </Link>
    );
  }
  return (
    <button type="button" className={className} disabled={disabled} onClick={action.onClick} aria-label={label} title={label}>
      {content}
    </button>
  );
}
