import { useEffect, useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router";

import { useAuth } from "../auth/AuthProvider";
import { THEME_LABELS, type ThemeChoice, useTheme } from "../theme/theme";
import { Icon, type IconName } from "./Icon";

const SECTIONS: { to: string; label: string; icon: IconName; end?: boolean }[] = [
  { to: "/", label: "Сводка", icon: "summary", end: true },
  { to: "/orders", label: "Заказы", icon: "orders" },
  { to: "/catalog/products", label: "Товары", icon: "products" },
  { to: "/catalog/categories", label: "Категории", icon: "categories" },
  { to: "/content/articles", label: "Статьи", icon: "articles" },
  { to: "/customers", label: "Клиенты", icon: "customers" },
  { to: "/settings", label: "Настройки", icon: "settings" },
];

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
          {SECTIONS.map((section) => (
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
        <Outlet />
      </main>
    </div>
  );
}
