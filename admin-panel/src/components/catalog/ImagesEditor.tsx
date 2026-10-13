import { type ChangeEvent, useState } from "react";

import { imagesService, type ProductImage } from "../../api/catalog";
import { ApiError } from "../../api/errors";

type Props = {
  productId: number;
  images: ProductImage[];
  onChanged: () => void;
};

const ACCEPT = "image/jpeg,image/png,image/webp";
const MAX_BYTES = 5 * 1024 * 1024;

function message(error: unknown): string {
  if (!(error instanceof ApiError)) return "Действие не выполнено.";
  return Object.values(error.fieldErrors)[0]?.[0] ?? error.message;
}

export function ImagesEditor({ productId, images, onChanged }: Props) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run(action: () => Promise<unknown>) {
    setBusy(true);
    setError(null);
    try {
      await action();
    } catch (err) {
      setError(message(err));
    } finally {
      setBusy(false);
      onChanged();
    }
  }

  function upload(event: ChangeEvent<HTMLInputElement>) {
    const files = Array.from(event.target.files ?? []);
    event.target.value = "";
    const tooBig = files.find((file) => file.size > MAX_BYTES);
    if (tooBig) {
      setError(`Файл «${tooBig.name}» больше 5 МБ.`);
      return;
    }
    void run(async () => {
      // По одному: порядок загрузки = порядок в галерее, ошибка не теряет уже загруженные.
      for (const file of files) await imagesService.upload(productId, file);
    });
  }

  function move(index: number, delta: number) {
    const ids = images.map((image) => image.id);
    const target = index + delta;
    const current = ids[index];
    const other = ids[target];
    if (current === undefined || other === undefined) return;
    ids[index] = other;
    ids[target] = current;
    void run(() => imagesService.reorder(productId, ids));
  }

  return (
    <div className="card">
      <h2>Фото</h2>
      <p className="muted">Первое фото — обложка в каталоге. JPEG, PNG или WebP до 5 МБ, не больше 10 штук.</p>
      {error ? <p className="alert">{error}</p> : null}
      <div className="gallery">
        {images.map((image, index) => (
          <figure key={image.id} className="gallery-item">
            <img src={image.url} alt={`Фото ${index + 1}`} />
            <figcaption className="actions">
              <button
                type="button"
                className="button button-ghost"
                aria-label="Левее"
                disabled={busy || index === 0}
                onClick={() => move(index, -1)}
              >
                ←
              </button>
              <button
                type="button"
                className="button button-ghost"
                aria-label="Правее"
                disabled={busy || index === images.length - 1}
                onClick={() => move(index, 1)}
              >
                →
              </button>
              <button
                type="button"
                className="button button-danger"
                disabled={busy}
                onClick={() => {
                  if (window.confirm("Удалить фото?")) void run(() => imagesService.remove(image.id));
                }}
              >
                Удалить
              </button>
            </figcaption>
          </figure>
        ))}
      </div>
      <label className="button button-ghost upload">
        {busy ? "Загрузка…" : "Загрузить фото"}
        <input type="file" accept={ACCEPT} multiple hidden disabled={busy} onChange={upload} />
      </label>
    </div>
  );
}
