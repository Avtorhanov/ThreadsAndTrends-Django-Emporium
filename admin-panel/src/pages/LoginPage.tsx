import { type FormEvent, useState } from "react";
import { Navigate } from "react-router";

import { ApiError } from "../api/errors";
import { useAuth } from "../auth/AuthProvider";
import { STORE_URL } from "../lib/site";

export function LoginPage() {
  const { status, login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  if (status === "signedIn") return <Navigate to="/" replace />;

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await login(email.trim(), password);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Не удалось войти.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="centered">
      <form className="card login-card" onSubmit={(event) => void handleSubmit(event)}>
        <div className="login-head">
          <span className="brand-mark" aria-hidden="true">
            DiDi
          </span>
          <div>
            <p className="eyebrow">DiDi shop</p>
            <h1>Вход администратора</h1>
          </div>
        </div>
        {error ? <p className="alert">{error}</p> : null}
        <label className="field">
          <span>Email</span>
          <input
            type="email"
            autoComplete="username"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            required
          />
        </label>
        <label className="field">
          <span>Пароль</span>
          <input
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
          />
        </label>
        <button type="submit" className="button" disabled={loading}>
          {loading ? "Вход…" : "Войти"}
        </button>
        <a className="login-store" href={STORE_URL}>
          Перейти в магазин
        </a>
      </form>
    </div>
  );
}
