import { useEffect, useRef } from "react";

export type PickOption = { value: string; label: string; tone?: string };

type Props = {
  title: string;
  options: PickOption[];
  onPick: (value: string) => void;
  onClose: () => void;
};

/** Выбор одного значения из короткого списка (статус товара и т. п.): шторка снизу на телефоне,
 * окно по центру на компьютере — как CategorySheet. */
export function PickSheet({ title, options, onPick, onClose }: Props) {
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
      <div className="sheet" role="dialog" aria-modal="true" aria-labelledby="pick-sheet-title">
        <span className="sheet-grip" aria-hidden="true" />
        <h2 id="pick-sheet-title">{title}</h2>
        <div className="sheet-list">
          {options.map((option, index) => (
            <button
              key={option.value}
              ref={index === 0 ? firstRef : undefined}
              type="button"
              className="sheet-row"
              onClick={() => onPick(option.value)}
            >
              <span className={`tone-dot tone-dot-${option.tone ?? "none"}`} aria-hidden="true" />
              <span className="sheet-row-label">{option.label}</span>
            </button>
          ))}
        </div>
        <button type="button" className="button button-ghost" onClick={onClose}>
          Отмена
        </button>
      </div>
    </div>
  );
}
