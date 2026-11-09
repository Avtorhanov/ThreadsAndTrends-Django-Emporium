import { type KeyboardEvent, useEffect, useState } from "react";

import { type Variant, variantsService } from "../../api/catalog";
import { ApiError } from "../../api/errors";
import { Icon } from "../Icon";

/** Изменение одного варианта, ещё не сохранённое. */
export type VariantPatch = { size: string; sku: string; stock: number };
export type VariantEdits = Map<number, VariantPatch>;

type Draft = { size: string; sku: string; stock: string };

type Props = {
  productId: number;
  variants: Variant[];
  onChanged: () => void;
  /** Несохранённые строки — наверх: их сохраняет и общая кнопка «Сохранить» товара. */
  onPendingChange?: (edits: VariantEdits) => void;
  /** Есть строка с неверным остатком: сохранять товар нельзя, иначе значение пропадёт молча. */
  onInvalidChange?: (invalid: boolean) => void;
};

function message(error: unknown): string {
  if (!(error instanceof ApiError)) return "Действие не выполнено.";
  return Object.values(error.fieldErrors)[0]?.[0] ?? error.message;
}

function draftOf(variant: Variant): Draft {
  return { size: variant.size ?? "", sku: variant.sku ?? "", stock: String(variant.stock ?? 0) };
}

export function validStock(value: string): boolean {
  const number = Number(value);
  return value.trim() !== "" && Number.isInteger(number) && number >= 0;
}

/** Остаток: поле и «−/+» по краям — на телефоне не нужно вызывать цифровую клавиатуру ради ±1. */
export function StockInput({ value, onChange, label }: { value: string; onChange: (value: string) => void; label: string }) {
  const number = Number(value);
  const step = (delta: number) => onChange(String(Math.max(0, (Number.isInteger(number) ? number : 0) + delta)));
  return (
    <span className="stock-input">
      <button type="button" aria-label={`${label}: меньше`} disabled={!(number > 0)} onClick={() => step(-1)}>
        −
      </button>
      <input
        type="number"
        inputMode="numeric"
        min={0}
        value={value}
        aria-label={label}
        aria-invalid={!validStock(value)}
        onChange={(event) => onChange(event.target.value)}
      />
      <button type="button" aria-label={`${label}: больше`} onClick={() => step(1)}>
        +
      </button>
    </span>
  );
}

/** Enter в поле строки — действие строки, а не отправка формы товара (строки — не формы:
 * редактор стоит внутри формы товара, вложенные <form> браузер не поддерживает). */
function onEnter(action: () => void) {
  return (event: KeyboardEvent) => {
    if (event.key !== "Enter") return;
    event.preventDefault();
    action();
  };
}

export function VariantsEditor({ productId, variants, onChanged, onPendingChange, onInvalidChange }: Props) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [drafts, setDrafts] = useState<Record<number, Draft>>({});
  const [all, setAll] = useState("1");
  const [size, setSize] = useState("");
  const [sku, setSku] = useState("");
  const [stock, setStock] = useState("0");
  const single = variants.length === 1 && !variants[0]?.size;

  // Данные с сервера обновились (сохранение, перезагрузка) — черновики строк сбрасываются.
  const version = variants.map((v) => `${v.id}:${v.size}:${v.sku}:${v.stock}`).join("|");
  useEffect(() => {
    setDrafts({});
  }, [version]);

  const rows = variants.map((variant) => {
    const original = draftOf(variant);
    const draft = drafts[variant.id] ?? original;
    const dirty = draft.size !== original.size || draft.sku !== original.sku || Number(draft.stock) !== variant.stock;
    return { variant, draft, dirty, valid: validStock(draft.stock) };
  });

  const pendingKey = rows
    .filter((row) => row.dirty && row.valid)
    .map((row) => `${row.variant.id}:${row.draft.size}:${row.draft.sku}:${row.draft.stock}`)
    .join("|");
  useEffect(() => {
    if (!onPendingChange) return;
    const edits: VariantEdits = new Map();
    for (const row of rows) {
      if (row.dirty && row.valid) {
        edits.set(row.variant.id, { size: row.draft.size, sku: row.draft.sku, stock: Number(row.draft.stock) });
      }
    }
    onPendingChange(edits);
    // rows пересчитываются каждый рендер; меняется только содержимое — pendingKey.
  }, [pendingKey]);

  const invalid = rows.filter((row) => !row.valid);
  const hasInvalid = invalid.length > 0;
  useEffect(() => {
    onInvalidChange?.(hasInvalid);
  }, [hasInvalid, onInvalidChange]);

  function edit(id: number, base: Draft, patch: Partial<Draft>) {
    setDrafts((current) => ({ ...current, [id]: { ...(current[id] ?? base), ...patch } }));
  }

  async function run(action: () => Promise<unknown>) {
    setBusy(true);
    setError(null);
    try {
      await action();
      onChanged();
      return true;
    } catch (err) {
      setError(message(err));
      return false;
    } finally {
      setBusy(false);
    }
  }

  function saveRow(id: number, draft: Draft) {
    if (!validStock(draft.stock)) return;
    void run(() => variantsService.update(id, { size: draft.size, sku: draft.sku, stock: Number(draft.stock) }));
  }

  /** «Всем размерам»: остаток у каждой строки — сохраняется вместе с товаром или ✓ у строк. */
  function applyAll() {
    if (!validStock(all)) return;
    setDrafts((current) => {
      const next = { ...current };
      for (const variant of variants) next[variant.id] = { ...(current[variant.id] ?? draftOf(variant)), stock: all };
      return next;
    });
  }

  async function add() {
    if (busy) return;
    const ok = await run(() =>
      variantsService.create(productId, { size: size.trim(), sku: sku.trim(), stock: Number(stock) || 0 }),
    );
    if (ok) {
      setSize("");
      setSku("");
      setStock("0");
    }
  }

  const anyDirty = rows.some((row) => row.dirty);

  return (
    <div className="card variants-card">
      <h2>Варианты и остатки</h2>
      <p className="muted small">
        {single
          ? "Товар без размеров — один вариант «Без размера». Чтобы добавить размеры, сначала впишите размер ему."
          : "Изменённые строки сохраняет «Сохранить» товара (или ✓ у строки)."}
      </p>
      {variants.length > 1 ? (
        <div className="variants-all">
          <span className="variants-all-label">Всем размерам</span>
          <StockInput value={all} onChange={setAll} label="Остаток всем размерам" />
          <button type="button" className="button button-ghost" disabled={busy || !validStock(all)} onClick={applyAll}>
            Задать
          </button>
        </div>
      ) : null}
      {error ? <p className="alert">{error}</p> : null}
      {hasInvalid ? (
        <p className="alert" role="alert">
          Остаток — целое число от 0: {invalid.map((row) => row.variant.size || "без размера").join(", ")}.
        </p>
      ) : anyDirty ? (
        <p className="note note-warning small" role="status">
          Остатки изменены — нажмите «Сохранить».
        </p>
      ) : null}
      <div className={busy ? "variants is-loading" : "variants"}>
        <div className="variant-head" aria-hidden="true">
          <span>Размер</span>
          <span>Артикул</span>
          <span>Остаток</span>
        </div>
        {rows.map(({ variant, draft, dirty, valid }) => {
          const title = variant.size || "Без размера";
          const base = draftOf(variant);
          const save = () => {
            if (dirty && valid) saveRow(variant.id, draft);
          };
          return (
            <div
              key={variant.id}
              className={dirty ? "variant-row is-dirty" : "variant-row"}
              role="group"
              aria-label={`Вариант ${title}`}
              onKeyDown={onEnter(save)}
            >
              <input
                className="variant-size"
                value={draft.size}
                placeholder="Без размера"
                maxLength={50}
                aria-label={`Размер: ${title}`}
                onChange={(e) => edit(variant.id, base, { size: e.target.value })}
              />
              <input
                className="variant-sku"
                value={draft.sku}
                maxLength={64}
                aria-label={`Артикул: ${title}`}
                onChange={(e) => edit(variant.id, base, { sku: e.target.value })}
              />
              <StockInput
                value={draft.stock}
                onChange={(value) => edit(variant.id, base, { stock: value })}
                label={`Остаток: ${title}`}
              />
              {dirty ? (
                <button
                  type="button"
                  className="icon-button variant-action is-save"
                  disabled={busy || !valid}
                  aria-label={`Сохранить ${title}`}
                  title="Сохранить строку"
                  onClick={save}
                >
                  <Icon name="check" size={18} />
                </button>
              ) : (
                <button
                  type="button"
                  className="icon-button variant-action is-delete"
                  disabled={busy}
                  aria-label={`Удалить ${title}`}
                  title="Удалить"
                  onClick={() => {
                    if (window.confirm(`Удалить вариант «${title}»?`)) void run(() => variantsService.remove(variant.id));
                  }}
                >
                  <Icon name="trash" size={18} />
                </button>
              )}
            </div>
          );
        })}
        <div className="variant-row variant-new" role="group" aria-label="Новый вариант" onKeyDown={onEnter(() => void add())}>
          <input
            className="variant-size"
            placeholder="Размер"
            value={size}
            maxLength={50}
            aria-label="Размер нового варианта"
            onChange={(e) => setSize(e.target.value)}
          />
          <input
            className="variant-sku"
            placeholder="Артикул — сам"
            value={sku}
            maxLength={64}
            aria-label="Артикул нового варианта (необязательно)"
            onChange={(e) => setSku(e.target.value)}
          />
          <StockInput value={stock} onChange={setStock} label="Остаток нового варианта" />
          <button
            type="button"
            className="icon-button variant-action is-add"
            disabled={busy}
            aria-label="Добавить вариант"
            title="Добавить вариант"
            onClick={() => void add()}
          >
            <Icon name="plus" size={18} />
          </button>
        </div>
      </div>
    </div>
  );
}
