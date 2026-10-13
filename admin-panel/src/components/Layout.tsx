import { NavLink, Outlet } from "react-router";

import { useAuth } from "../auth/AuthProvider";

export function Layout() {
  const { user, logout } = useAuth();
  return (
    <div className="shell">
      <header className="topbar">
        <span className="brand">DiDi-shop</span>
        <nav className="nav">
          <NavLink to="/orders">Заказы</NavLink>
          <NavLink to="/catalog/products">Товары</NavLink>
          <NavLink to="/catalog/categories">Категории</NavLink>
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
