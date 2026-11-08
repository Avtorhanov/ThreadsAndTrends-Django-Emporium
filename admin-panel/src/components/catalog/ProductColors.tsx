import { useState } from "react";
import { Link } from "react-router";

import { type Product, productsService } from "../../api/catalog";
import { ApiError } from "../../api/errors";
import { ColorLinkSheet } from "./ColorLinkSheet";

type Props = { product: Product; onChanged: () => void };

/** Цвета этой модели в карточке товара. Связывают — отметками в списке товаров или черновиков. */
export function ProductColors({ product, onChanged }: Props) {
  const [sheet, setSheet] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const siblings = product.color_siblings;

  async function unlink() {
    setError(null);
    try {
      await productsService.unlinkColor(product.id);
      onChanged();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Не удалось отвязать.");
    }
  }

  return (
    <div className="card stack-sm" role="group" aria-label="Цвета товара">
      <strong>Цвет: {product.color_name}</strong>
      <ul className="color-siblings">
        {siblings.map((item) => (
          <li key={item.id}>
            <Link to={`/catalog/products/${item.id}`}>{item.color_name}</Link>
            {item.is_draft ? <span className="muted small"> · черновик</span> : item.is_active ? null : <span className="muted small"> · скрыт</span>}
          </li>
        ))}
      </ul>
      {error ? (
        <p className="alert alert-error" role="alert">
          {error}
        </p>
      ) : null}
      <div className="color-siblings-actions">
        <button type="button" className="button button-ghost" onClick={() => setSheet(true)}>
          Изменить названия
        </button>
        <button type="button" className="button button-ghost" onClick={() => void unlink()}>
          Отвязать
        </button>
      </div>
      {sheet ? (
        <ColorLinkSheet
          rows={[
            { id: product.id, name: product.name, cover_url: product.cover_url, color_name: product.color_name },
            ...siblings,
          ]}
          onDone={() => {
            setSheet(false);
            onChanged();
          }}
          onClose={() => setSheet(false)}
        />
      ) : null}
    </div>
  );
}
