import { Link } from "react-router";

/** «← Раздел» — отдельной строкой над заголовком экрана, одинаково на всех экранах панели. */
export function BackLink({ to, label }: { to: string; label: string }) {
  return (
    <Link to={to} className="page-back">
      <span aria-hidden="true">←</span> {label}
    </Link>
  );
}
