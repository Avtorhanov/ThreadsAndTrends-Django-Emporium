import { type FormEvent, type ReactNode, useState } from "react";

import { ApiError, type FieldErrors } from "../api/errors";
import { authService } from "../auth/authService";
import { useAuth } from "../auth/AuthProvider";
import { Icon } from "../components/Icon";
import { storeUrl } from "../lib/site";

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

export function AccountPage() {
  const { user } = useAuth();
  const [values, setValues] = useState(EMPTY);
  const [shown, setShown] = useState(false);
  const [errors, setErrors] = useState<FieldErrors>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [done, setDone] = useState(false);
  const [saving, setSaving] = useState(false);

  const role = user?.is_owner ? "Владелец" : "Сотрудник";
  const name = [user?.first_name, user?.last_name].filter(Boolean).join(" ");

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
      if (err instanceof ApiError) {
        setErrors(err.fieldErrors);
        if (!Object.keys(err.fieldErrors).length || err.fieldErrors.non_field_errors) setFormError(err.message);
      } else {
        setFormError("Не удалось сменить пароль.");
      }
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="stack account-page">
      <div className="page-header">
        <h1>Аккаунт</h1>
      </div>

      <section className="card form-card">
        <h2>Вход в панель</h2>
        <dl className="account-facts">
          <div>
            <dt>Email</dt>
            <dd>{user?.email}</dd>
          </div>
          {name ? (
            <div>
              <dt>Имя</dt>
              <dd>{name}</dd>
            </div>
          ) : null}
          <div>
            <dt>Роль</dt>
            <dd>{role}</dd>
          </div>
        </dl>
      </section>

      <form className="card form-card" onSubmit={(event) => void submit(event)} noValidate>
        <h2>Смена пароля</h2>
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
