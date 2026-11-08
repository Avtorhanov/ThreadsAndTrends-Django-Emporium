import { type ReactNode, Suspense, useEffect } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router";

import { AuthProvider, useAuth } from "./auth/AuthProvider";
import { Layout } from "./components/Layout";
import { lazyPage, prefetchPages } from "./lib/lazyPage";
import { LoginPage } from "./pages/LoginPage";
import { SummaryPage } from "./pages/SummaryPage";

// Остальные экраны — отдельными кусками (lib/lazyPage.ts).
const LookSection = lazyPage(() => import("./components/LookSection"), "LookSection");
const AccountPage = lazyPage(() => import("./pages/AccountPage"), "AccountPage");
const ArticleEditPage = lazyPage(() => import("./pages/ArticleEditPage"), "ArticleEditPage");
const ArticlesPage = lazyPage(() => import("./pages/ArticlesPage"), "ArticlesPage");
const CategoriesPage = lazyPage(() => import("./pages/CategoriesPage"), "CategoriesPage");
const CustomersPage = lazyPage(() => import("./pages/CustomersPage"), "CustomersPage");
const OrderDetailPage = lazyPage(() => import("./pages/OrderDetailPage"), "OrderDetailPage");
const OrdersPage = lazyPage(() => import("./pages/OrdersPage"), "OrdersPage");
const ProductBatchPage = lazyPage(() => import("./pages/ProductBatchPage"), "ProductBatchPage");
const ProductDraftsPage = lazyPage(() => import("./pages/ProductDraftsPage"), "ProductDraftsPage");
const ProductEditPage = lazyPage(() => import("./pages/ProductEditPage"), "ProductEditPage");
const ProductsPage = lazyPage(() => import("./pages/ProductsPage"), "ProductsPage");
const HomeEditorPage = lazyPage(() => import("./pages/HomeEditorPage"), "HomeEditorPage");
const PanelLookPage = lazyPage(() => import("./pages/PanelLookPage"), "PanelLookPage");
const SettingsPage = lazyPage(() => import("./pages/SettingsPage"), "SettingsPage");
const StaffPage = lazyPage(() => import("./pages/StaffPage"), "StaffPage");
const ThemePage = lazyPage(() => import("./pages/ThemePage"), "ThemePage");

// "/panel" в боевой сборке; в превью — "/<репозиторий>/panel" (vite.config.ts, VITE_BASE).
const BASENAME = import.meta.env.BASE_URL.replace(/\/$/, "");

function RequireStaff({ children }: { children: ReactNode }) {
  const { status } = useAuth();
  if (status === "signedOut") return <Navigate to="/login" replace />;
  return children;
}

function Gate({ children }: { children: ReactNode }) {
  const { status, retry } = useAuth();
  useEffect(() => {
    if (status === "signedIn") prefetchPages();
  }, [status]);
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
          <Suspense fallback={<div className="centered">Загрузка…</div>}>
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
                <Route path="/catalog/products/batch" element={<ProductBatchPage />} />
                <Route path="/catalog/products/drafts" element={<ProductDraftsPage />} />
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
                <Route path="/account" element={<AccountPage />} />
              </Route>
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </Suspense>
        </Gate>
      </AuthProvider>
    </BrowserRouter>
  );
}
