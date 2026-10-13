import { NavLink, Outlet } from "react-router";

import { useAuth } from "../auth/AuthProvider";

export function Layout() {
  const { user, logout } = useAuth();
  return (
    <div className="shell">
      <header className="topbar">
        <span className="brand">DiDi-shop</span>
        <nav className="nav">
          {/* Каталог и заказы появятся в сессиях 3 и 5. */}
          <NavLink to="/customers">Клиенты</NavLink>
        </nav>
        <div className="topbar-user">
          <span className="muted">{user?.email}</span>
          <button type="button" className="button button-ghost" onClick={() => void logout()}>
            Выйти
          </button>
        </div>
      </header>
      <main className="content">
        <Outlet />
      </main>
    </div>
  );
}
