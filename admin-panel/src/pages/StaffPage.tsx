import { type FormEvent, useState } from "react";

import { ApiError } from "../api/errors";
import {
  type AccessLevel,
  LEVEL_LABELS,
  PRESETS,
  STAFF_SECTIONS,
  type StaffMember,
  type StaffPermissions,
  sectionsOf,
  staffService,
} from "../api/staff";
import { useLoader } from "../hooks/useCatalog";

const dateFormat = new Intl.DateTimeFormat("ru-RU", { dateStyle: "short", timeStyle: "short" });

function message(error: unknown): string {
  if (!(error instanceof ApiError)) return "Действие не выполнено.";
  return Object.values(error.fieldErrors)[0]?.[0] ?? error.message;
}

/** Таблица прав: строка — раздел, три уровня. */
function PermissionsEditor({
  value,
  disabled,
  onChange,
}: {
  value: StaffPermissions;
  disabled?: boolean;
  onChange: (next: StaffPermissions) => void;
}) {
  return (
    <div className="perm-table" role="table" aria-label="Права по разделам">
      {STAFF_SECTIONS.map((section) => (
        <div key={section.key} className="perm-row" role="row">
          <span role="rowheader">{section.label}</span>
          <div className="perm-levels" role="radiogroup" aria-label={section.label}>
            {(Object.keys(LEVEL_LABELS) as AccessLevel[]).map((level) => (
              <button
                key={level}
                type="button"
                role="radio"
                aria-checked={value[section.key] === level}
                className={value[section.key] === level ? `is-on perm-${level}` : undefined}
                disabled={disabled}
                onClick={() => onChange({ ...value, [section.key]: level })}
              >
                {LEVEL_LABELS[level]}
              </button>
            ))}
          </div>
        </div>
      ))}
      <p className="muted small">«Настройки и оплата» и «Сотрудники» — только у владельца.</p>
    </div>
  );
}

function Presets({ onPick, disabled }: { onPick: (value: StaffPermissions) => void; disabled?: boolean }) {
  return (
    <div className="perm-presets">
      <span className="muted small">Шаблоны:</span>
      {PRESETS.map((preset) => (
        <button
          key={preset.key}
          type="button"
          className="button button-outline"
          disabled={disabled}
          onClick={() => onPick(preset.permissions)}
        >
          {preset.label}
        </button>
      ))}
    </div>
  );
}

function MemberCard({ member, onChanged }: { member: StaffMember; onChanged: (next: StaffMember) => void }) {
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  async function run(action: () => Promise<StaffMember | void>, done?: string) {
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      const result = await action();
      if (result) onChanged(result);
      if (done) setNotice(done);
    } catch (err) {
      setError(message(err));
    } finally {
      setBusy(false);
    }
  }

  const status = member.is_owner
    ? { text: "Владелец", tone: "badge-active" }
    : !member.is_active
      ? { text: "Отключён", tone: "badge-blocked" }
      : member.invited
        ? { text: "Приглашён", tone: "badge-info" }
        : { text: "Активен", tone: "badge-active" };

  return (
    <li className="card staff-card">
      <div className="staff-head">
        <span className="staff-avatar" aria-hidden="true">
          {(member.first_name || member.email).slice(0, 1).toUpperCase()}
        </span>
        <span className="staff-name">
          <strong>{member.first_name || member.email}</strong>
          <span className="muted small">
            {member.email}
            {member.last_login ? ` · был ${dateFormat.format(new Date(member.last_login))}` : ""}
          </span>
        </span>
        <span className={`badge ${status.tone}`}>{status.text}</span>
        {member.is_owner ? null : (
          <button type="button" className="button button-ghost" onClick={() => setOpen((v) => !v)} aria-expanded={open}>
            {open ? "Свернуть" : "Права"}
          </button>
        )}
      </div>
      {member.is_owner ? <p className="muted small">Все разделы, включая настройки и сотрудников. Права владельца не меняются.</p> : null}
      {error ? <p className="alert">{error}</p> : null}
      {notice ? <p className="note note-success">{notice}</p> : null}
      {open && !member.is_owner ? (
        <div className="staff-body">
          <Presets
            disabled={busy}
            onPick={(permissions) => void run(() => staffService.update(member.id, { permissions }), "Права сохранены.")}
          />
          <PermissionsEditor
            value={sectionsOf(member)}
            disabled={busy}
            onChange={(permissions) => void run(() => staffService.update(member.id, { permissions }))}
          />
          <div className="status-actions">
            {member.invited && member.is_active ? (
              <button
                type="button"
                className="button button-outline"
                disabled={busy}
                onClick={() => void run(() => staffService.resend(member.id), "Приглашение отправлено ещё раз.")}
              >
                Отправить приглашение ещё раз
              </button>
            ) : null}
            <button
              type="button"
              className={member.is_active ? "button button-danger" : "button"}
              disabled={busy}
              onClick={() => {
                if (member.is_active && !window.confirm(`Отключить ${member.email}? Вход в панель закроется сразу.`)) return;
                void run(() => staffService.update(member.id, { is_active: !member.is_active }));
              }}
            >
              {member.is_active ? "Отключить" : "Включить снова"}
            </button>
          </div>
        </div>
      ) : null}
    </li>
  );
}

function InviteForm({ onInvited }: { onInvited: (member: StaffMember) => void }) {
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [permissions, setPermissions] = useState<StaffPermissions>(PRESETS[0]!.permissions);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      onInvited(await staffService.invite({ email, first_name: name, permissions }));
      setEmail("");
      setName("");
    } catch (err) {
      setError(message(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="card stack" onSubmit={submit}>
      <h2>Пригласить сотрудника</h2>
      <p className="muted small">
        Придёт письмо с кодом: сотрудник сам задаст пароль и войдёт в панель. Код действует 3 дня.
      </p>
      <div className="staff-invite-fields">
        <label className="field">
          <span>Email</span>
          <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
        </label>
        <label className="field">
          <span>Имя</span>
          <input value={name} maxLength={150} onChange={(e) => setName(e.target.value)} />
        </label>
      </div>
      <Presets onPick={setPermissions} disabled={busy} />
      <PermissionsEditor value={permissions} disabled={busy} onChange={setPermissions} />
      {error ? <p className="alert">{error}</p> : null}
      <div>
        <button type="submit" className="button button-accent" disabled={busy}>
          {busy ? "Отправляем…" : "Пригласить"}
        </button>
      </div>
    </form>
  );
}

/** Панель → «Сотрудники» (только владелец): права по разделам сохраняются сразу. */
export function StaffPage() {
  const loader = useLoader(() => staffService.list(), "staff", "Не удалось загрузить сотрудников.");
  const members = loader.data ?? [];

  function replace(next: StaffMember) {
    loader.set(members.map((item) => (item.id === next.id ? next : item)));
  }

  return (
    <section className="stack">
      <div className="page-header">
        <h1>Сотрудники</h1>
        {loader.data ? <span className="muted">Всего: {members.length}</span> : null}
      </div>
      {loader.error ? <p className="alert">{loader.error}</p> : null}
      {loader.loading && !loader.data ? <p className="muted">Загрузка…</p> : null}
      <div className="staff-grid">
        <ul className="staff-list">
          {members.map((member) => (
            <MemberCard key={member.id} member={member} onChanged={replace} />
          ))}
        </ul>
        <InviteForm onInvited={(member) => loader.set([...members, member])} />
      </div>
    </section>
  );
}
