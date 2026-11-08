import { type FormEvent, useState } from "react";

import { productsService } from "../../api/catalog";
import { ApiError } from "../../api/errors";

export type ColorRow = { id: number; name: string; cover_url: string | null; color_name: string };

type Props = {
  rows: ColorRow[];
  onDone: (updated: number) => void;
  onClose: () => void;
};

/** Связка товаров как цветов одной модели; для уже связанных — смена названий цветов. */
export function ColorLinkSheet({ rows, onDone, onClose }: Props) {
  const [names, setNames] = useState(() => new Map(rows.map((row) => [row.id, row.color_name])));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const filled = rows.every((row) => (names.get(row.id) ?? "").trim());

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const items = rows.map((row) => ({ id: row.id, color_name: names.get(row.id) ?? "" }));
      const result = await productsService.linkColors(items);
      onDone(result.updated);
    } catch (err) {
      setError(
        err instanceof ApiError
          ? (Object.values(err.fieldErrors)[0]?.[0] ?? err.message)
          : "Не удалось связать цвета.",
      );
      setBusy(false);
    }
  }

  return (
    <div className="sheet-layer">
      <button type="button" className="sheet-scrim" aria-label="Закрыть" onClick={onClose} />
      <form className="sheet" role="dialog" aria-modal="true" aria-labelledby="color-sheet-title" onSubmit={submit}>
        <span className="sheet-grip" aria-hidden="true" />
        <h2 id="color-sheet-title">Цвета одной модели</h2>
        <p className="muted small">Покупатель переключает цвета на карточке товара. Видны только опубликованные.</p>
        <div className="sheet-list">
          {rows.map((row) => (
            <label key={row.id} className="color-link-row">
              {row.cover_url ? <img src={row.cover_url} alt="" /> : <span className="color-link-empty" aria-hidden="true" />}
              <span className="color-link-name muted small">{row.name}</span>
              <input
                value={names.get(row.id) ?? ""}
                maxLength={40}
                placeholder="Цвет"
                aria-label={`Цвет: ${row.name}`}
                onChange={(event) => setNames((prev) => new Map(prev).set(row.id, event.target.value))}
              />
            </label>
          ))}
        </div>
        {error ? (
          <p className="alert alert-error" role="alert">
            {error}
          </p>
        ) : null}
        <button type="submit" className="button button-accent" disabled={busy || !filled}>
          Сохранить цвета
        </button>
        <button type="button" className="button button-ghost" onClick={onClose}>
          Отмена
        </button>
      </form>
    </div>
  );
}
