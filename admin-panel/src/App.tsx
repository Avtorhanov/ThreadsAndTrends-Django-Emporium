import type { ReactNode } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router";

import { AuthProvider, useAuth } from "./auth/AuthProvider";
import { Layout } from "./components/Layout";
import { LookSection } from "./components/LookSection";
import { ArticleEditPage } from "./pages/ArticleEditPage";
import { ArticlesPage } from "./pages/ArticlesPage";
import { CategoriesPage } from "./pages/CategoriesPage";
import { CustomersPage } from "./pages/CustomersPage";
import { LoginPage } from "./pages/LoginPage";
import { OrderDetailPage } from "./pages/OrderDetailPage";
import { OrdersPage } from "./pages/OrdersPage";
import { ProductEditPage } from "./pages/ProductEditPage";
import { ProductsPage } from "./pages/ProductsPage";
import { HomeEditorPage } from "./pages/HomeEditorPage";
import { PanelLookPage } from "./pages/PanelLookPage";
import { SettingsPage } from "./pages/SettingsPage";
import { StaffPage } from "./pages/StaffPage";
import { ThemePage } from "./pages/ThemePage";
import { SummaryPage } from "./pages/SummaryPage";

// "/panel" в боевой сборке; в превью — "/<репозиторий>/panel" (vite.config.ts, VITE_BASE).
const BASENAME = import.meta.env.BASE_URL.replace(/\/$/, "");

function RequireStaff({ children }: { children: ReactNode }) {
  const { status } = useAuth();
  if (status === "signedOut") return <Navigate to="/login" replace />;
  return children;
}

function Gate({ children }: { children: ReactNode }) {
  const { status, retry } = useAuth();
  if (status === "loading") return <div className="centered">Загрузка…</div>;
  if (status === "error") {
    return (
      <div className="centered">
        <p>Сервер недоступен.</p>
        <button type="button" className="button" onClick={retry}>
          Повторить
        </button>
      </div>
    );
  }
  return children;
}

export function App() {
  return (
    <BrowserRouter basename={BASENAME}>
      <AuthProvider>
        <Gate>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route
              element={
                <RequireStaff>
                  <Layout />
                </RequireStaff>
              }
            >
              <Route index element={<SummaryPage />} />
              <Route path="/orders" element={<OrdersPage />} />
              <Route path="/orders/:id" element={<OrderDetailPage />} />
              <Route path="/customers" element={<CustomersPage />} />
              <Route path="/catalog" element={<Navigate to="/catalog/products" replace />} />
              <Route path="/catalog/products" element={<ProductsPage />} />
              <Route path="/catalog/products/new" element={<ProductEditPage />} />
              <Route path="/catalog/products/:id" element={<ProductEditPage />} />
              <Route path="/catalog/categories" element={<CategoriesPage />} />
              <Route path="/content/articles" element={<ArticlesPage />} />
              <Route path="/content/articles/new" element={<ArticleEditPage />} />
              <Route path="/content/articles/:id" element={<ArticleEditPage />} />
              <Route path="/look" element={<LookSection />}>
                <Route index element={null} />
                <Route path="home" element={<HomeEditorPage />} />
                <Route path="theme" element={<ThemePage />} />
                <Route path="panel" element={<PanelLookPage />} />
              </Route>
              {/* Прежние адреса разделов — в «Внешний вид». */}
              <Route path="/home" element={<Navigate to="/look/home" replace />} />
              <Route path="/theme" element={<Navigate to="/look/theme" replace />} />
              <Route path="/staff" element={<StaffPage />} />
              <Route path="/settings" element={<SettingsPage />} />
            </Route>
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Gate>
      </AuthProvider>
    </BrowserRouter>
  );
}
