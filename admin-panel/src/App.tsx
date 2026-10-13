import type { ReactNode } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router";

import { AuthProvider, useAuth } from "./auth/AuthProvider";
import { Layout } from "./components/Layout";
import { CustomersPage } from "./pages/CustomersPage";
import { LoginPage } from "./pages/LoginPage";

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
    <BrowserRouter basename="/panel">
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
              <Route index element={<Navigate to="/customers" replace />} />
              <Route path="/customers" element={<CustomersPage />} />
            </Route>
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Gate>
      </AuthProvider>
    </BrowserRouter>
  );
}
