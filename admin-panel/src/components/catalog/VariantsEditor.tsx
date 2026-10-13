import { type FormEvent, useState } from "react";

import { type Variant, variantsService } from "../../api/catalog";
import { ApiError } from "../../api/errors";

type Props = {
  productId: number;
  variants: Variant[];
  onChanged: () => void;
};

function message(error: unknown): string {
  if (!(error instanceof ApiError)) return "Действие не выполнено.";
  return Object.values(error.fieldErrors)[0]?.[0] ?? error.message;
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

  return (
    <tr>
      <td>
        <input value={size} placeholder="Без размера" maxLength={50} onChange={(e) => setSize(e.target.value)} />
      </td>
      <td>
        <input value={sku} maxLength={64} onChange={(e) => setSku(e.target.value)} />
      </td>
      <td>
        <input
          className="input-narrow"
          type="number"
          min={0}
          value={stock}
          onChange={(e) => setStock(e.target.value)}
        />
      </td>
      <td className="actions">
        <button
          type="button"
          className="button button-ghost"
          disabled={busy || !dirty || !valid}
          onClick={() => onSave({ size, sku, stock: stockNumber })}
        >
          Сохранить
        </button>
        <button type="button" className="button button-danger" disabled={busy} onClick={onDelete}>
          Удалить
        </button>
      </td>
    </tr>
  );
}

export function VariantsEditor({ productId, variants, onChanged }: Props) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [size, setSize] = useState("");
  const [sku, setSku] = useState("");
  const [stock, setStock] = useState("0");

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
    <div className="card">
      <h2>Варианты и остатки</h2>
      <p className="muted">
        Товар без размеров — один вариант «Без размера». Чтобы добавить размеры, сначала укажите размер у него.
      </p>
      {error ? <p className="alert">{error}</p> : null}
      <div className="table-wrap">
        <table className={busy ? "table is-loading" : "table"}>
          <thead>
            <tr>
              <th>Размер</th>
              <th>Артикул</th>
              <th>Остаток</th>
              <th aria-label="Действия" />
            </tr>
          </thead>
          <tbody>
            {variants.map((variant) => (
              <VariantRow
                // Ключ с версией данных: после сохранения строка инициализируется заново.
                key={`${variant.id}:${variant.size}:${variant.sku}:${variant.stock}`}
                variant={variant}
                busy={busy}
                onSave={(patch) => void run(() => variantsService.update(variant.id, patch))}
                onDelete={() => {
                  if (window.confirm("Удалить вариант?")) void run(() => variantsService.remove(variant.id));
                }}
              />
            ))}
          </tbody>
        </table>
      </div>
      <form className="filters inline-form" onSubmit={add}>
        <input placeholder="Размер" value={size} maxLength={50} onChange={(e) => setSize(e.target.value)} />
        <input placeholder="Артикул (необязательно)" value={sku} maxLength={64} onChange={(e) => setSku(e.target.value)} />
        <input
          className="input-narrow"
          type="number"
          min={0}
          value={stock}
          onChange={(e) => setStock(e.target.value)}
        />
        <button type="submit" className="button button-ghost" disabled={busy}>
          Добавить вариант
        </button>
      </form>
    </div>
  );
}
