import { type FormEvent, useState } from "react";

import { type Variant, variantsService } from "../../api/catalog";
import { ApiError } from "../../api/errors";
import { Icon } from "../Icon";

type Props = {
  productId: number;
  variants: Variant[];
  onChanged: () => void;
};

function message(error: unknown): string {
  if (!(error instanceof ApiError)) return "Действие не выполнено.";
  return Object.values(error.fieldErrors)[0]?.[0] ?? error.message;
}

/** Остаток: поле и «−/+» по краям — на телефоне не нужно вызывать цифровую клавиатуру ради ±1. */
function StockInput({ value, onChange, label }: { value: string; onChange: (value: string) => void; label: string }) {
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
        onChange={(event) => onChange(event.target.value)}
      />
      <button type="button" aria-label={`${label}: больше`} onClick={() => step(1)}>
        +
      </button>
    </span>
  );
}

function VariantRow({ variant, busy, onSave, onDelete }: {
  variant: Variant;
  busy: boolean;
  onSave: (patch: { size: string; sku: string; stock: number }) => void;
  onDelete: () => void;
}) {
  const [size, setSize] = useState(variant.size ?? "");
  const [sku, setSku] = useState(variant.sku ?? "");
  const [stock, setStock] = useState(String(variant.stock ?? 0));
  const stockNumber = Number(stock);
  const valid = Number.isInteger(stockNumber) && stockNumber >= 0;
  const dirty =
    size !== (variant.size ?? "") || sku !== (variant.sku ?? "") || stockNumber !== (variant.stock ?? 0);
  const title = variant.size || "Без размера";

  function submit(event: FormEvent) {
    event.preventDefault();
    if (dirty && valid) onSave({ size, sku, stock: stockNumber });
  }

  // Строка — своя форма: Enter в любом поле сохраняет только её.
  return (
    <form className={dirty ? "variant-row is-dirty" : "variant-row"} onSubmit={submit}>
      <input
        className="variant-size"
        value={size}
        placeholder="Без размера"
        maxLength={50}
        aria-label={`Размер: ${title}`}
        onChange={(e) => setSize(e.target.value)}
      />
      <input
        className="variant-sku"
        value={sku}
        maxLength={64}
        aria-label={`Артикул: ${title}`}
        onChange={(e) => setSku(e.target.value)}
      />
      <StockInput value={stock} onChange={setStock} label={`Остаток: ${title}`} />
      {dirty ? (
        <button
          type="submit"
          className="icon-button variant-action is-save"
          disabled={busy || !valid}
          aria-label={`Сохранить ${title}`}
          title="Сохранить"
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
          onClick={onDelete}
        >
          <Icon name="trash" size={18} />
        </button>
      )}
    </form>
  );
}

export function VariantsEditor({ productId, variants, onChanged }: Props) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [size, setSize] = useState("");
  const [sku, setSku] = useState("");
  const [stock, setStock] = useState("0");
  const single = variants.length === 1 && !variants[0]?.size;

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

  async function add(event: FormEvent) {
    event.preventDefault();
    const ok = await run(() =>
      variantsService.create(productId, { size: size.trim(), sku: sku.trim(), stock: Number(stock) || 0 }),
    );
    if (ok) {
      setSize("");
      setSku("");
      setStock("0");
    }
  }

  return (
    <div className="card variants-card">
      <h2>Варианты и остатки</h2>
      <p className="muted small">
        {single
          ? "Товар без размеров — один вариант «Без размера». Чтобы добавить размеры, сначала впишите размер ему."
          : "Изменения строки сохраняет ✓ справа — отдельно от кнопки «Сохранить» товара."}
      </p>
      {error ? <p className="alert">{error}</p> : null}
      <div className={busy ? "variants is-loading" : "variants"}>
        <div className="variant-head" aria-hidden="true">
          <span>Размер</span>
          <span>Артикул</span>
          <span>Остаток</span>
        </div>
        {variants.map((variant) => (
          <VariantRow
            // Ключ с версией данных: после сохранения строка инициализируется заново.
            key={`${variant.id}:${variant.size}:${variant.sku}:${variant.stock}`}
            variant={variant}
            busy={busy}
            onSave={(patch) => void run(() => variantsService.update(variant.id, patch))}
            onDelete={() => {
              if (window.confirm(`Удалить вариант «${variant.size || "Без размера"}»?`)) {
                void run(() => variantsService.remove(variant.id));
              }
            }}
          />
        ))}
        <form className="variant-row variant-new" onSubmit={add}>
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
            type="submit"
            className="icon-button variant-action is-add"
            disabled={busy}
            aria-label="Добавить вариант"
            title="Добавить вариант"
          >
            <Icon name="plus" size={18} />
          </button>
        </form>
      </div>
    </div>
  );
}
