import { type FormEvent, useEffect, useState } from "react";

import { type BlockKind, type SiteBlock, blocksService } from "../../api/blocks";
import { ApiError, type FieldErrors } from "../../api/errors";
import { useAuth } from "../../auth/AuthProvider";

type ContactKind = Exclude<BlockKind, "link">;

const KINDS: { kind: ContactKind; label: string; placeholder: string; hint: string }[] = [
  { kind: "whatsapp", label: "WhatsApp", placeholder: "+7 900 123-45-67", hint: "Номер телефона" },
  { kind: "telegram", label: "Telegram", placeholder: "@didishop", hint: "Имя (@…) или ссылка t.me/…" },
  { kind: "vk", label: "ВКонтакте", placeholder: "didishop", hint: "Короткое имя или ссылка vk.com/…" },
  { kind: "phone", label: "Телефон", placeholder: "+7 900 123-45-67", hint: "Номер для звонка" },
  { kind: "email", label: "Почта", placeholder: "shop@example.ru", hint: "Адрес электронной почты" },
];
const LABELS = Object.fromEntries(KINDS.map((item) => [item.kind, item.label])) as Record<string, string>;

type Draft = { kind: ContactKind; value: string; note: string };
const EMPTY: Draft = { kind: "whatsapp", value: "", note: "" };

function errorsOf(err: unknown): { form: string; fields: FieldErrors } {
  if (err instanceof ApiError) return { form: err.message, fields: err.fieldErrors };
  return { form: "Не удалось сохранить.", fields: {} };
}

/**
 * Каналы связи для вкладки «Контакты» на сайте и в приложении. Те же блоки, что правятся
 * на сайте двойным нажатием; пока раздел не меняли — показываются значения из .env.
 */
export function ContactsSettings() {
  const { user } = useAuth();
  const level = user?.permissions ? user.permissions.storefront : "edit";
  const readOnly = level !== "edit";
  const [blocks, setBlocks] = useState<SiteBlock[] | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  // Номер редактируемого канала; -1 — новый канал; null — форма закрыта.
  const [editing, setEditing] = useState<number | null>(null);
  const [draft, setDraft] = useState<Draft>(EMPTY);
  const [formError, setFormError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});

  useEffect(() => {
    if (level === "none") return;
    let cancelled = false;
    blocksService
      .list("contacts")
      .then((list) => {
        if (!cancelled) setBlocks(list);
      })
      .catch((err: unknown) => {
        if (!cancelled) setLoadError(errorsOf(err).form);
      });
    return () => {
      cancelled = true;
    };
  }, [level]);

  if (level === "none") return null;

  /** Значения по умолчанию (.env) приходят без id — первое изменение переносит их в БД. */
  async function withIds(): Promise<SiteBlock[]> {
    const current = blocks ?? [];
    if (current.every((block) => block.id != null)) return current;
    const list = await blocksService.customize("contacts");
    setBlocks(list);
    return list;
  }

  async function run(action: (list: SiteBlock[]) => Promise<unknown>): Promise<boolean> {
    setBusy(true);
    setFormError(null);
    setFieldErrors({});
    try {
      await action(await withIds());
      setBlocks(await blocksService.list("contacts"));
      return true;
    } catch (err) {
      const { form, fields } = errorsOf(err);
      setFormError(Object.keys(fields).length ? null : form);
      setFieldErrors(fields);
      return false;
    } finally {
      setBusy(false);
    }
  }

  function open(index: number) {
    const block = index >= 0 ? blocks?.[index] : undefined;
    setDraft(
      block ? { kind: (block.kind ?? "whatsapp") as ContactKind, value: block.value, note: block.note ?? "" } : EMPTY,
    );
    setFormError(null);
    setFieldErrors({});
    setEditing(index);
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (editing === null) return;
    const index = editing;
    const body = { kind: draft.kind, value: draft.value.trim(), note: draft.note.trim(), title: "" };
    const done = await run((list) => {
      const block = list[index];
      if (index < 0 || !block) return blocksService.create({ area: "contacts", ...body });
      return blocksService.update(block.id, body);
    });
    if (done) setEditing(null);
  }

  function move(index: number, step: -1 | 1) {
    void run((list) => {
      const ids = list.map((block) => block.id);
      const [moved] = ids.splice(index, 1);
      if (moved !== undefined) ids.splice(index + step, 0, moved);
      return blocksService.reorder("contacts", ids);
    });
  }

  function remove(index: number) {
    const block = blocks?.[index];
    if (!block || !window.confirm(`Убрать канал «${LABELS[block.kind ?? ""] ?? ""}: ${block.value}»?`)) return;
    void run(async (list) => {
      const target = list[index];
      if (target) await blocksService.remove(target.id);
    });
  }

  const kindInfo = KINDS.find((item) => item.kind === draft.kind) ?? {
    kind: draft.kind,
    label: "",
    placeholder: "",
    hint: "Значение",
  };
  const form = (
    <form className="contact-form" onSubmit={(event) => void submit(event)} noValidate>
      <label className="field">
        Канал
        <select value={draft.kind} onChange={(e) => setDraft({ ...draft, kind: e.target.value as ContactKind })}>
          {KINDS.map((item) => (
            <option key={item.kind} value={item.kind}>
              {item.label}
            </option>
          ))}
        </select>
        {fieldErrors.kind ? <span className="field-error">{fieldErrors.kind[0]}</span> : null}
      </label>
      <label className="field">
        {kindInfo.hint}
        <input
          value={draft.value}
          maxLength={300}
          placeholder={kindInfo.placeholder}
          inputMode={draft.kind === "email" ? "email" : draft.kind === "whatsapp" || draft.kind === "phone" ? "tel" : "text"}
          autoFocus
          onChange={(e) => setDraft({ ...draft, value: e.target.value })}
        />
        {fieldErrors.value ? <span className="field-error">{fieldErrors.value[0]}</span> : null}
      </label>
      <label className="field">
        Подпись <span className="muted small">— необязательно</span>
        <input
          value={draft.note}
          maxLength={160}
          placeholder="Например: «Ответим за 15 минут»"
          onChange={(e) => setDraft({ ...draft, note: e.target.value })}
        />
      </label>
      {formError ? <p className="alert">{formError}</p> : null}
      <div className="actions">
        <button type="submit" className="button" disabled={busy || !draft.value.trim()}>
          {busy ? "Сохранение…" : editing !== null && editing < 0 ? "Добавить" : "Сохранить"}
        </button>
        <button type="button" className="button button-ghost" disabled={busy} onClick={() => setEditing(null)}>
          Отмена
        </button>
      </div>
    </form>
  );

  return (
    <section className="card form-grid settings-wide contacts-settings">
      <h2>Контакты</h2>
      <p className="muted">
        Каналы связи на вкладке «Контакты» сайта и приложения и в кнопке «Узнать» у товаров с ценой по запросу.
        Пустой список — вкладка показывает только статьи.
      </p>
      {loadError ? <p className="alert">{loadError}</p> : null}
      {blocks === null && !loadError ? <p className="muted small">Загрузка…</p> : null}
      {blocks ? (
        <ul className="contact-list">
          {blocks.map((block, index) => (
            <li key={block.id ?? `default-${index}`} className="contact-row">
              {editing === index ? (
                form
              ) : (
                <>
                  <span className="contact-main">
                    <span className="contact-kind">{LABELS[block.kind ?? ""] ?? block.kind}</span>
                    <span className="contact-value">{block.value}</span>
                    {block.note ? <span className="muted small">{block.note}</span> : null}
                  </span>
                  {readOnly ? null : (
                    <span className="contact-actions">
                      <button
                        type="button"
                        className="icon-button"
                        aria-label="Выше"
                        title="Выше"
                        disabled={busy || index === 0}
                        onClick={() => move(index, -1)}
                      >
                        ↑
                      </button>
                      <button
                        type="button"
                        className="icon-button"
                        aria-label="Ниже"
                        title="Ниже"
                        disabled={busy || index === blocks.length - 1}
                        onClick={() => move(index, 1)}
                      >
                        ↓
                      </button>
                      <button type="button" className="button button-ghost" disabled={busy} onClick={() => open(index)}>
                        Изменить
                      </button>
                      <button type="button" className="button button-ghost" disabled={busy} onClick={() => remove(index)}>
                        Убрать
                      </button>
                    </span>
                  )}
                </>
              )}
            </li>
          ))}
          {blocks.length === 0 && editing === null ? <li className="muted">Каналов пока нет.</li> : null}
        </ul>
      ) : null}
      {editing !== null && editing < 0 ? form : null}
      {!readOnly && blocks && editing === null ? (
        <div>
          <button type="button" className="button button-outline" disabled={busy} onClick={() => open(-1)}>
            Добавить канал
          </button>
        </div>
      ) : null}
      {formError && editing === null ? <p className="alert">{formError}</p> : null}
    </section>
  );
}
