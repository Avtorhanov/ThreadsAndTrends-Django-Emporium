import { Navigate, NavLink, Outlet, useLocation } from "react-router";

import type { StaffUser } from "../auth/authService";
import { useAuth } from "../auth/AuthProvider";
import { ViewOnlyProvider } from "./ViewOnly";

type Access = keyof StaffUser["permissions"];

/** Раздел «Внешний вид»: всё, что меняет вид магазина и панели, — в одном месте.
 * «Главная» и «Тема магазина» — по праву «Главная и тема», «Категории» (меню витрины) —
 * по своему праву «Категории»; «Панель» — личный выбор сотрудника, доступен всем. */
const TABS: { to: string; label: string; access?: Access }[] = [
  { to: "/look/home", label: "Главная", access: "storefront" },
  { to: "/look/categories", label: "Категории", access: "categories" },
  { to: "/look/theme", label: "Тема магазина", access: "storefront" },
  { to: "/look/panel", label: "Панель" },
];

export function LookSection() {
  const { user } = useAuth();
  const { pathname } = useLocation();
  const permissions = user?.permissions;
  const levelOf = (access?: Access) => (access && permissions ? permissions[access] : "edit");
  const tabs = TABS.filter((tab) => levelOf(tab.access) !== "none");
  const current = TABS.find((tab) => pathname === tab.to || pathname.startsWith(`${tab.to}/`));

  if (!current) return <Navigate to={tabs[0]?.to ?? "/look/panel"} replace />;
  const level = levelOf(current.access);
  if (level === "none") return <Navigate to={tabs[0]?.to ?? "/look/panel"} replace />;

  return (
    <div className="look-section">
      <nav className="subnav" aria-label="Внешний вид">
        {tabs.map((tab) => (
          <NavLink key={tab.to} to={tab.to}>
            {tab.label}
          </NavLink>
        ))}
      </nav>
      {level === "view" ? (
        <p className="note note-info view-only">Только просмотр: изменения в этом разделе вам недоступны.</p>
      ) : null}
      <ViewOnlyProvider value={level === "view"}>
        <Outlet />
      </ViewOnlyProvider>
    </div>
  );
}
