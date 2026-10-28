import { useEffect, useState } from "react";
import { Navigate, NavLink, Outlet, useLocation } from "react-router";

import type { StaffUser } from "../auth/authService";
import { useAuth } from "../auth/AuthProvider";
import { THEME_LABELS, type ThemeChoice, useTheme } from "../theme/theme";
import { Icon, type IconName } from "./Icon";

type Access = keyof StaffUser["permissions"];

const SECTIONS: { to: string; label: string; icon: IconName; access: Access; end?: boolean }[] = [
  { to: "/", label: "Сводка", icon: "summary", access: "summary", end: true },
  { to: "/orders", label: "Заказы", icon: "orders", access: "orders" },
  { to: "/catalog/products", label: "Товары", icon: "products", access: "products" },
  { to: "/catalog/categories", label: "Категории", icon: "categories", access: "categories" },
  { to: "/content/articles", label: "Статьи", icon: "articles", access: "articles" },
  { to: "/customers", label: "Клиенты", icon: "customers", access: "customers" },
  { to: "/home", label: "Главная", icon: "home", access: "storefront" },
  { to: "/theme", label: "Тема", icon: "palette", access: "storefront" },
  { to: "/settings", label: "Настройки", icon: "settings", access: "settings" },
  { to: "/staff", label: "Сотрудники", icon: "customers", access: "staff" },
];

/** Раздел текущей страницы (самый длинный совпавший путь). */
function sectionFor(pathname: string) {
  return SECTIONS.filter((item) =>
    item.to === "/" ? pathname === "/" : pathname === item.to || pathname.startsWith(`${item.to}/`),
  ).sort((a, b) => b.to.length - a.to.length)[0];
}

const THEME_ICONS: Record<ThemeChoice, IconName> = { system: "system", light: "sun", dark: "moon" };

/** Витрина — корень сайта: панель живёт в /panel/ (на превью — /<репозиторий>/panel/). */
const STORE_URL = import.meta.env.BASE_URL.replace(/panel\/?$/, "");

/** Открыть магазин из любого раздела — посмотреть изменения глазами покупателя. */
function StoreLink() {
  return (
    <a
      className="icon-button store-link"
      href={STORE_URL}
      target="_blank"
      rel="noopener"
      aria-label="Открыть магазин"
      title="Открыть магазин"
    >
      <Icon name="store" />
    </a>
  );
}

function Brand() {
  return (
    <span className="brand">
      <span className="brand-mark" aria-hidden="true">
        Di
      </span>
      <span className="brand-name">
        DiDi<span className="brand-accent">-shop</span>
      </span>
    </span>
  );
}

function ThemeSwitch() {
  const { choice, change } = useTheme();
  return (
    <div className="theme-switch" role="radiogroup" aria-label="Тема оформления">
      {(Object.keys(THEME_LABELS) as ThemeChoice[]).map((value) => (
        <button
          key={value}
          type="button"
          role="radio"
          aria-checked={choice === value}
          aria-label={THEME_LABELS[value]}
          title={THEME_LABELS[value]}
          className={choice === value ? "theme-option is-active" : "theme-option"}
          onClick={() => change(value)}
        >
          <Icon name={THEME_ICONS[value]} size={18} />
        </button>
      ))}
    </div>
  );
}

export function Layout() {
  const { user, logout } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);
  const location = useLocation();

  // Переход по разделу закрывает шторку на телефоне.
  useEffect(() => setMenuOpen(false), [location.pathname]);

  // Права сотрудника: недоступные разделы скрыты, только чтение — с плашкой. Проверяет сервер.
  const permissions = user?.permissions;
  const visible = SECTIONS.filter((item) => !permissions || permissions[item.access] !== "none");
  const current = sectionFor(location.pathname);
  const level = current && permissions ? permissions[current.access] : "edit";

  useEffect(() => {
    if (!menuOpen) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") setMenuOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [menuOpen]);

  return (
    <div className={menuOpen ? "shell menu-open" : "shell"}>
      <header className="mobilebar">
        <button
          type="button"
          className="icon-button"
          aria-label="Открыть меню"
          aria-expanded={menuOpen}
          aria-controls="sidebar"
          onClick={() => setMenuOpen(true)}
        >
          <Icon name="menu" />
        </button>
        <Brand />
        <StoreLink />
      </header>

      <div className="scrim" aria-hidden="true" onClick={() => setMenuOpen(false)} />

      <aside id="sidebar" className="sidebar" aria-label="Разделы панели">
        <div className="sidebar-head">
          <Brand />
          <StoreLink />
          <button
            type="button"
            className="icon-button sidebar-close"
            aria-label="Закрыть меню"
            onClick={() => setMenuOpen(false)}
          >
            <Icon name="close" />
          </button>
        </div>
        <p className="sidebar-caption">Панель администратора</p>
        <nav className="nav">
          {visible.map((section) => (
            <NavLink key={section.to} to={section.to} end={section.end}>
              <Icon name={section.icon} />
              {section.label}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-foot">
          <ThemeSwitch />
          <div className="sidebar-user">
            <span className="muted small user-email" title={user?.email}>
              {user?.email}
            </span>
            <button
              type="button"
              className="icon-button"
              aria-label="Выйти"
              title="Выйти"
              onClick={() => void logout()}
            >
              <Icon name="logout" />
            </button>
          </div>
        </div>
      </aside>

      <main className="content">
        {level === "none" ? (
          visible[0] && location.pathname === "/" ? (
            <Navigate to={visible[0].to} replace />
          ) : (
            <section className="stack">
              <h1>Нет доступа</h1>
              <p className="muted">Этот раздел вам не открыт. Права выдаёт владелец магазина.</p>
            </section>
          )
        ) : (
          <>
            {level === "view" ? (
              <p className="note note-info view-only">Только просмотр: изменения в этом разделе вам недоступны.</p>
            ) : null}
            <Outlet />
          </>
        )}
      </main>
    </div>
  );
}
