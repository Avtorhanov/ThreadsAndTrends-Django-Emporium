import { type FormEvent, type ReactNode, useEffect, useState } from "react";

import { ApiError, type FieldErrors } from "../api/errors";
import { type EmailPending, authService } from "../auth/authService";
import { useAuth } from "../auth/AuthProvider";
import { Icon } from "../components/Icon";
import { storeUrl } from "../lib/site";
import { BackLink } from "../components/BackLink";

function FieldError({ errors, name }: { errors: FieldErrors; name: string }) {
  const message = errors[name]?.[0];
  return message ? <span className="field-error">{message}</span> : null;
}

/** Поле пароля с кнопкой «показать» — на телефоне длинный пароль проще проверить глазами. */
function PasswordField({
  label,
  value,
  autoComplete,
  shown,
  onToggle,
  onChange,
  error,
}: {
  label: string;
  value: string;
  autoComplete: string;
  shown: boolean;
  onToggle: () => void;
  onChange: (value: string) => void;
  error: ReactNode;
}) {
  return (
    <label className="field">
      {label}
      <span className="password-input">
        <input
          type={shown ? "text" : "password"}
          autoComplete={autoComplete}
          value={value}
          maxLength={128}
          onChange={(event) => onChange(event.target.value)}
          required
        />
        <button
          type="button"
          className="icon-button"
          aria-label={shown ? "Скрыть пароль" : "Показать пароль"}
          aria-pressed={shown}
          onClick={onToggle}
        >
          <Icon name={shown ? "eyeOff" : "eye"} size={18} />
        </button>
      </span>
      {error}
    </label>
  );
}

const EMPTY = { old: "", next: "", repeat: "" };

function apiErrors(err: unknown, fallback: string): { fields: FieldErrors; message: string | null } {
  if (!(err instanceof ApiError)) return { fields: {}, message: fallback };
  const general = !Object.keys(err.fieldErrors).length || Boolean(err.fieldErrors.non_field_errors);
  return { fields: err.fieldErrors, message: general ? err.message : null };
}

/** Имя и фамилия — сохраняются сразу. */
function NameCard() {
  const { user, updateUser } = useAuth();
  const [first, setFirst] = useState(user?.first_name ?? "");
  const [last, setLast] = useState(user?.last_name ?? "");
  const [errors, setErrors] = useState<FieldErrors>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [done, setDone] = useState(false);
  const [saving, setSaving] = useState(false);
  const changed = first.trim() !== (user?.first_name ?? "") || last.trim() !== (user?.last_name ?? "");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setErrors({});
    setFormError(null);
    try {
      const next = await authService.updateProfile(first.trim(), last.trim());
      updateUser(next);
      setFirst(next.first_name);
      setLast(next.last_name);
      setDone(true);
    } catch (err) {
      const parsed = apiErrors(err, "Не удалось сохранить.");
      setErrors(parsed.fields);
      setFormError(parsed.message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <form className="card form-card" onSubmit={(event) => void submit(event)} noValidate>
      <h2>Имя</h2>
      {formError ? <p className="alert">{formError}</p> : null}
      {done && !changed ? (
        <p className="note note-success" role="status">
          Сохранено.
        </p>
      ) : null}
      <div className="account-names">
        <label className="field">
          Имя
          <input
            value={first}
            maxLength={150}
            autoComplete="given-name"
            onChange={(event) => {
              setFirst(event.target.value);
              setDone(false);
            }}
          />
          <FieldError errors={errors} name="first_name" />
        </label>
        <label className="field">
          Фамилия
          <input
            value={last}
            maxLength={150}
            autoComplete="family-name"
            onChange={(event) => {
              setLast(event.target.value);
              setDone(false);
            }}
          />
          <FieldError errors={errors} name="last_name" />
        </label>
      </div>
      <div className="form-actions">
        <button type="submit" className="button" disabled={saving || !changed}>
          {saving ? "Сохранение…" : "Сохранить"}
        </button>
      </div>
    </form>
  );
}

/** Email — логин: код на новый адрес, на прежний — уведомление. */
function EmailCard() {
  const { user, updateUser } = useAuth();
  const [pending, setPending] = useState<EmailPending | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [newEmail, setNewEmail] = useState("");
  const [password, setPassword] = useState("");
  const [shown, setShown] = useState(false);
  const [code, setCode] = useState("");
  const [errors, setErrors] = useState<FieldErrors>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let alive = true;
    authService
      .pendingEmail()
      .then((value) => {
        if (alive) setPending(value);
      })
      .catch(() => undefined)
      .finally(() => {
        if (alive) setLoaded(true);
      });
    return () => {
      alive = false;
    };
  }, []);

  async function run(action: () => Promise<void>, fallback: string) {
    setBusy(true);
    setErrors({});
    setFormError(null);
    setNotice(null);
    try {
      await action();
    } catch (err) {
      const parsed = apiErrors(err, fallback);
      setErrors(parsed.fields);
      setFormError(parsed.message);
    } finally {
      setBusy(false);
    }
  }

  const request = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    void run(async () => {
      const next = await authService.requestEmailChange(newEmail.trim(), password);
      setPending(next);
      setPassword("");
      setNotice(`Код отправлен на ${next.new_email}.`);
    }, "Не удалось отправить код.");
  };

  const confirm = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    void run(async () => {
      const next = await authService.confirmEmailChange(code.trim());
      updateUser(next);
      setPending(null);
      setCode("");
      setNewEmail("");
      setNotice(`Email изменён: теперь входите с ${next.email}.`);
    }, "Не удалось подтвердить код.");
  };

  const cancel = () =>
    void run(async () => {
      await authService.cancelEmailChange();
      setPending(null);
      setCode("");
    }, "Не удалось отменить.");

  const until = pending
    ? new Date(pending.expires_at).toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" })
    : "";

  return (
    <section className="card form-card">
      <h2>Email</h2>
      <dl className="account-facts">
        <div>
          <dt>Сейчас</dt>
          <dd>{user?.email}</dd>
        </div>
      </dl>
      {formError ? <p className="alert">{formError}</p> : null}
      {notice ? (
        <p className="note note-success" role="status">
          {notice}
        </p>
      ) : null}
      {!loaded ? null : pending ? (
        <form className="form-grid" onSubmit={confirm} noValidate>
          <p className="muted">
            Код отправлен на <strong>{pending.new_email}</strong>, действует до {until}.
          </p>
          <label className="field">
            Код из письма
            <input
              value={code}
              inputMode="numeric"
              autoComplete="one-time-code"
              maxLength={6}
              placeholder="000000"
              onChange={(event) => setCode(event.target.value.replace(/\D/g, ""))}
            />
            <FieldError errors={errors} name="code" />
          </label>
          <div className="form-actions">
            <button type="submit" className="button" disabled={busy || code.length !== 6}>
              Подтвердить email
            </button>
            <button type="button" className="button button-ghost" disabled={busy} onClick={cancel}>
              Отменить смену
            </button>
          </div>
        </form>
      ) : (
        <form className="form-grid" onSubmit={request} noValidate>
          <label className="field">
            Новый email
            <input
              type="email"
              value={newEmail}
              autoComplete="email"
              maxLength={254}
              onChange={(event) => setNewEmail(event.target.value)}
            />
            <FieldError errors={errors} name="new_email" />
          </label>
          <PasswordField
            label="Текущий пароль"
            value={password}
            autoComplete="current-password"
            shown={shown}
            onToggle={() => setShown((value) => !value)}
            onChange={setPassword}
            error={<FieldError errors={errors} name="password" />}
          />
          <p className="muted small">Пока вы не введёте код из письма, вход — по прежнему email.</p>
          <div className="form-actions">
            <button type="submit" className="button" disabled={busy || !newEmail.trim() || !password}>
              Получить код
            </button>
          </div>
        </form>
      )}
    </section>
  );
}

export function AccountPage() {
  const { user } = useAuth();
  const [values, setValues] = useState(EMPTY);
  const [shown, setShown] = useState(false);
  const [errors, setErrors] = useState<FieldErrors>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [done, setDone] = useState(false);
  const [saving, setSaving] = useState(false);

  const role = user?.is_owner ? "Владелец" : "Сотрудник";

  function set(patch: Partial<typeof EMPTY>) {
    setValues((current) => ({ ...current, ...patch }));
    setDone(false);
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFormError(null);
    setDone(false);
    if (values.next !== values.repeat) {
      setErrors({ repeat: ["Пароли не совпадают."] });
      return;
    }
    setErrors({});
    setSaving(true);
    try {
      await authService.changePassword(values.old, values.next);
      setValues(EMPTY);
      setDone(true);
    } catch (err) {
      const parsed = apiErrors(err, "Не удалось сменить пароль.");
      setErrors(parsed.fields);
      setFormError(parsed.message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="stack account-page">
      <div className="page-header">
        <BackLink to="/" label="Сводка" />
        <h1>Аккаунт</h1>
        <span className="muted small">{role}</span>
      </div>

      <NameCard />
      <EmailCard />

      <form className="card form-card" onSubmit={(event) => void submit(event)} noValidate>
        <h2>Пароль</h2>
        <p className="muted">
          Эта вкладка останется в панели, на других устройствах и в приложении нужно будет войти заново.
        </p>
        {formError ? <p className="alert">{formError}</p> : null}
        {done ? (
          <p className="note note-success" role="status">
            Пароль изменён.
          </p>
        ) : null}
        <PasswordField
          label="Текущий пароль"
          value={values.old}
          autoComplete="current-password"
          shown={shown}
          onToggle={() => setShown((value) => !value)}
          onChange={(old) => set({ old })}
          error={<FieldError errors={errors} name="old_password" />}
        />
        <PasswordField
          label="Новый пароль"
          value={values.next}
          autoComplete="new-password"
          shown={shown}
          onToggle={() => setShown((value) => !value)}
          onChange={(next) => set({ next })}
          error={<FieldError errors={errors} name="new_password" />}
        />
        <PasswordField
          label="Новый пароль ещё раз"
          value={values.repeat}
          autoComplete="new-password"
          shown={shown}
          onToggle={() => setShown((value) => !value)}
          onChange={(repeat) => set({ repeat })}
          error={<FieldError errors={errors} name="repeat" />}
        />
        <p className="muted small">Не короче 8 символов, не только цифры и не похож на email.</p>
        <div className="form-actions">
          <button
            type="submit"
            className="button"
            disabled={saving || !values.old || !values.next || !values.repeat}
          >
            {saving ? "Сохранение…" : "Сменить пароль"}
          </button>
          <a className="muted small" href={storeUrl(`password-reset/?email=${encodeURIComponent(user?.email ?? "")}`)}>
            Не помню текущий пароль
          </a>
        </div>
      </form>
    </section>
  );
}
