import { useEffect, useRef } from "react";

import type { Category } from "../../api/catalog";
import { type BatchCategory, categoryLabel } from "./batch";

type Props = {
  title: string;
  note?: string;
  categories: BatchCategory[];
  all: Category[];
  /** Сколько товаров уже в категории (в пачке или среди черновиков). */
  counts: Map<number, number>;
  onPick: (category: BatchCategory) => void;
  onClose: () => void;
};

/** Выбор категории: шторка снизу на телефоне, окно по центру на компьютере. */
export function CategorySheet({ title, note, categories, all, counts, onPick, onClose }: Props) {
  const firstRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    firstRef.current?.focus();
    const close = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    document.addEventListener("keydown", close);
    return () => document.removeEventListener("keydown", close);
  }, [onClose]);

  return (
    <div className="sheet-layer">
      <button type="button" className="sheet-scrim" aria-label="Закрыть" onClick={onClose} />
      <div className="sheet" role="dialog" aria-modal="true" aria-labelledby="category-sheet-title">
        <span className="sheet-grip" aria-hidden="true" />
        <h2 id="category-sheet-title">{title}</h2>
        {note ? <p className="muted small">{note}</p> : null}
        <div className="sheet-list">
          {categories.map((category, index) => {
            const count = counts.get(category.id) ?? 0;
            return (
              <button
                key={category.id}
                ref={index === 0 ? firstRef : undefined}
                type="button"
                className="sheet-row"
                onClick={() => onPick(category)}
              >
                <span className={`cat-dot cat-tone-${category.tone}`} aria-hidden="true" />
                <span className="sheet-row-label">{categoryLabel(category, all)}</span>
                {count ? <span className="muted small">уже {count}</span> : null}
              </button>
            );
          })}
          {categories.length === 0 ? (
            <p className="muted">Нет категорий для товаров — создайте их во «Внешнем виде» → «Категории».</p>
          ) : null}
        </div>
        <button type="button" className="button button-ghost" onClick={onClose}>
          Отмена
        </button>
      </div>
    </div>
  );
}
