import { Navigate, NavLink, Outlet, useLocation } from "react-router";

import { useAuth } from "../auth/AuthProvider";

/** Раздел «Внешний вид»: всё, что меняет вид магазина и панели, — в одном месте.
 * «Главная витрины» и «Тема витрины» — по праву «Главная и тема»; «Оформление панели» —
 * личный выбор каждого сотрудника, доступен всем. */
const TABS = [
  { to: "/look/home", label: "Главная", shop: true },
  { to: "/look/theme", label: "Тема магазина", shop: true },
  { to: "/look/panel", label: "Панель", shop: false },
] as const;

export function LookSection() {
  const { user } = useAuth();
  const { pathname } = useLocation();
  const shopLevel = user?.permissions ? user.permissions.storefront : "edit";
  const tabs = TABS.filter((tab) => !tab.shop || shopLevel !== "none");
  const current = TABS.find((tab) => pathname === tab.to || pathname.startsWith(`${tab.to}/`));

  if (!current) return <Navigate to={tabs[0]?.to ?? "/look/panel"} replace />;
  if (current.shop && shopLevel === "none") return <Navigate to="/look/panel" replace />;

  return (
    <div className="look-section">
      <nav className="subnav" aria-label="Внешний вид">
        {tabs.map((tab) => (
          <NavLink key={tab.to} to={tab.to}>
            {tab.label}
          </NavLink>
        ))}
      </nav>
      {current.shop && shopLevel === "view" ? (
        <p className="note note-info view-only">Только просмотр: изменения в этом разделе вам недоступны.</p>
      ) : null}
      <Outlet />
    </div>
  );
}
