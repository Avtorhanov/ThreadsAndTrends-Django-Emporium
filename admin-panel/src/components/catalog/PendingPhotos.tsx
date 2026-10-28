import { type ChangeEvent, useEffect, useMemo, useState } from "react";

export const MAX_PRODUCT_IMAGES = 10;
const ACCEPT = "image/jpeg,image/png,image/webp";
const MAX_BYTES = 5 * 1024 * 1024;

/**
 * Фото нового товара до сохранения: можно выбрать сразу несколько, поменять порядок,
 * сделать обложкой и убрать. Загружаются после создания товара — в этом же порядке.
 */
export function PendingPhotos({ files, onChange }: { files: File[]; onChange: (files: File[]) => void }) {
  const [error, setError] = useState<string | null>(null);
  const previews = useMemo(() => files.map((file) => URL.createObjectURL(file)), [files]);
  useEffect(() => () => previews.forEach((url) => URL.revokeObjectURL(url)), [previews]);

  function pick(event: ChangeEvent<HTMLInputElement>) {
    const picked = Array.from(event.target.files ?? []);
    event.target.value = "";
    const tooBig = picked.filter((file) => file.size > MAX_BYTES);
    const fitting = picked.filter((file) => file.size <= MAX_BYTES);
    const room = MAX_PRODUCT_IMAGES - files.length;
    const messages: string[] = [];
    if (tooBig.length) messages.push(`Больше 5 МБ, пропущено: ${tooBig.map((file) => file.name).join(", ")}.`);
    if (fitting.length > room) messages.push(`Не больше ${MAX_PRODUCT_IMAGES} фото — лишние не добавлены.`);
    setError(messages.length ? messages.join(" ") : null);
    if (room > 0) onChange([...files, ...fitting.slice(0, room)]);
  }

  function move(index: number, delta: number) {
    const target = index + delta;
    if (target < 0 || target >= files.length) return;
    const next = [...files];
    const [file] = next.splice(index, 1);
    if (file) next.splice(target, 0, file);
    onChange(next);
  }

  function makeCover(index: number) {
    const next = [...files];
    const [file] = next.splice(index, 1);
    if (file) onChange([file, ...next]);
  }

  return (
    <div className="pending-photos">
      <label className="drop-zone">
        <strong>Выберите фото — можно сразу несколько</strong>
        <span className="muted small">
          JPEG, PNG или WebP до 5 МБ · до {MAX_PRODUCT_IMAGES} фото · первое — обложка
        </span>
        <span className="button">Выбрать фото</span>
        <input
          type="file"
          accept={ACCEPT}
          multiple
          hidden
          disabled={files.length >= MAX_PRODUCT_IMAGES}
          onChange={pick}
        />
      </label>
      {error ? <p className="field-error">{error}</p> : null}
      {files.length ? (
        <div className="photo-grid">
          {files.map((file, index) => (
            <figure key={`${file.name}:${file.size}:${file.lastModified}`} className="photo-tile">
              <img src={previews[index]} alt={`Фото ${index + 1}`} />
              {index === 0 ? <span className="photo-cover">Обложка</span> : null}
              <figcaption>
                <button type="button" aria-label="Левее" disabled={index === 0} onClick={() => move(index, -1)}>
                  ←
                </button>
                <button
                  type="button"
                  aria-label="Сделать обложкой"
                  disabled={index === 0}
                  onClick={() => makeCover(index)}
                >
                  ★
                </button>
                <button
                  type="button"
                  aria-label="Правее"
                  disabled={index === files.length - 1}
                  onClick={() => move(index, 1)}
                >
                  →
                </button>
                <button
                  type="button"
                  aria-label="Убрать фото"
                  className="photo-remove"
                  onClick={() => onChange(files.filter((_, i) => i !== index))}
                >
                  ×
                </button>
              </figcaption>
            </figure>
          ))}
        </div>
      ) : null}
      <span className="muted small">
        {files.length} из {MAX_PRODUCT_IMAGES}. Загрузятся при сохранении товара; ошибка загрузки не сотрёт введённое.
      </span>
    </div>
  );
}
