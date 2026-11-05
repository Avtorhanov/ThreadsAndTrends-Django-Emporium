/**
 * Масштаб интерфейса: 7 вариантов в процентах (ключи — из tokens.json, textScale), «−»/«+» по
 * краям. Весь интерфейс меняется пропорционально — текст, отступы, кнопки, фото.
 */
export function ScalePicker<T extends string>({
  label,
  values,
  value,
  disabled,
  onChange,
}: {
  label: string;
  values: readonly T[];
  value: T;
  disabled?: boolean;
  onChange: (next: T) => void;
}) {
  const index = values.indexOf(value);
  const step = (delta: number) => {
    const next = values[index + delta];
    if (next !== undefined) onChange(next);
  };
  return (
    <div className="scale-picker">
      <button
        type="button"
        className="scale-step"
        aria-label="Мельче"
        disabled={disabled || index <= 0}
        onClick={() => step(-1)}
      >
        A<sup>−</sup>
      </button>
      <div className="scale-options" role="radiogroup" aria-label={label}>
        {values.map((item) => (
          <button
            key={item}
            type="button"
            role="radio"
            aria-checked={item === value}
            aria-label={`${item} %`}
            className={item === value ? "is-on" : undefined}
            disabled={disabled}
            onClick={() => onChange(item)}
          >
            {item}
          </button>
        ))}
      </div>
      <button
        type="button"
        className="scale-step scale-step-up"
        aria-label="Крупнее"
        disabled={disabled || index >= values.length - 1}
        onClick={() => step(1)}
      >
        A<sup>+</sup>
      </button>
    </div>
  );
}
