import { type ChangeEvent, useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate } from "react-router";

import { imagesService, productsService } from "../api/catalog";
import { ApiError } from "../api/errors";
import { BackLink } from "../components/BackLink";
import { Icon } from "../components/Icon";
import {
  BATCH_SIZES,
  type BatchCategory,
  DEFAULT_BATCH_SIZES,
  MAX_BATCH_PHOTOS,
  batchCategories,
  categoryLabel,
  plural,
  products as productsText,
} from "../components/catalog/batch";
import { CategorySheet } from "../components/catalog/CategorySheet";
import { MAX_PRODUCT_IMAGES } from "../components/catalog/PendingPhotos";
import { useCategories, useLabels } from "../hooks/useCatalog";
import { parseRublesToKopecks } from "../lib/money";

const ACCEPT = "image/jpeg,image/png,image/webp";
const MAX_BYTES = 5 * 1024 * 1024;

type Photo = { key: string; file: File; url: string };
type Group = { id: number; keys: string[]; category: number | null };
type Step = "photos" | "common";

export type BatchResult = { created: number; failed: string[] };

/** Шаги пачки — те же на всех трёх экранах (третий — «Черновики»). */
export function BatchSteps({ current }: { current: 0 | 1 | 2 }) {
  return (
    <ol className="batch-steps" aria-label="Шаги">
      {["Фото", "Общее", "Черновики"].map((label, index) => (
        <li
          key={label}
          className={index === current ? "is-current" : index < current ? "is-done" : undefined}
          aria-current={index === current ? "step" : undefined}
        >
          {index + 1} · {label}
        </li>
      ))}
    </ol>
  );
}

/**
 * «Товары → Добавить пачкой»: фото раскладываются по товарам (по одному, группой или все
 * сразу), товарам задаются категории, затем общие поля — и создаются черновики.
 * Раскладка живёт в браузере до создания; черновики — на сервере.
 */
export function ProductBatchPage() {
  const navigate = useNavigate();
  const categories = useCategories();
  const labels = useLabels();
  const [step, setStep] = useState<Step>("photos");
  const [photos, setPhotos] = useState<Photo[]>([]);
  const [groupOf, setGroupOf] = useState<Record<string, number>>({});
  const [catOf, setCatOf] = useState<Record<number, number>>({});
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [sheet, setSheet] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [price, setPrice] = useState("");
  const [sizes, setSizes] = useState<string[]>(DEFAULT_BATCH_SIZES);
  const [stock, setStock] = useState(0);
  const [fallback, setFallback] = useState<number | null>(null);
  const [progress, setProgress] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const seq = useRef(0);
  const photosRef = useRef<Photo[]>([]);
  photosRef.current = photos;

  useEffect(() => () => photosRef.current.forEach((photo) => URL.revokeObjectURL(photo.url)), []);

  // Разложенные фото живут только в браузере: уход со страницы их теряет.
  const unsaved = photos.length > 0 && progress === null;
  useEffect(() => {
    if (!unsaved) return;
    const warn = (event: BeforeUnloadEvent) => event.preventDefault();
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [unsaved]);

  const all = categories.data ?? [];
  const leaf = useMemo(() => batchCategories(all), [all]);
  const byId = useMemo(() => new Map(leaf.map((item) => [item.id, item])), [leaf]);

  // Статус по умолчанию — «В наличии», если он есть в справочнике.
  useEffect(() => {
    if (status !== null || !labels.data) return;
    const inStock = labels.data.find((item) => item.name.toLowerCase() === "в наличии");
    setStatus(inStock ? String(inStock.id) : "");
  }, [labels.data, status]);

  const groups: Group[] = useMemo(() => {
    const order: number[] = [];
    const keys = new Map<number, string[]>();
    for (const photo of photos) {
      const id = groupOf[photo.key];
      if (id === undefined) continue;
      if (!keys.has(id)) {
        keys.set(id, []);
        order.push(id);
      }
      keys.get(id)?.push(photo.key);
    }
    return order.map((id) => ({ id, keys: keys.get(id) ?? [], category: catOf[id] ?? null }));
  }, [photos, groupOf, catOf]);

  const groupNumber = new Map(groups.map((group, index) => [group.id, index + 1]));
  const loose = photos.filter((photo) => groupOf[photo.key] === undefined).map((photo) => photo.key);
  const selectedGroups = [
    ...new Set([...selected].map((key) => groupOf[key]).filter((id): id is number => id !== undefined)),
  ];
  const selectedLoose = [...selected].filter((key) => groupOf[key] === undefined).length;
  const uncategorized = groups.filter((group) => group.category === null || !byId.has(group.category));

  function nextId() {
    seq.current += 1;
    return seq.current;
  }

  function pick(event: ChangeEvent<HTMLInputElement>) {
    const picked = Array.from(event.target.files ?? []);
    event.target.value = "";
    const tooBig = picked.filter((file) => file.size > MAX_BYTES);
    const fitting = picked.filter((file) => file.size <= MAX_BYTES);
    const room = MAX_BATCH_PHOTOS - photos.length;
    const messages: string[] = [];
    if (tooBig.length) messages.push(`Больше 5 МБ, пропущено: ${tooBig.map((file) => file.name).join(", ")}.`);
    if (fitting.length > room) messages.push(`Не больше ${MAX_BATCH_PHOTOS} фото за раз — лишние не добавлены.`);
    setNotice(messages.length ? messages.join(" ") : null);
    const added = fitting.slice(0, Math.max(0, room)).map((file) => ({
      key: `${Date.now()}-${Math.random().toString(36).slice(2)}`,
      file,
      url: URL.createObjectURL(file),
    }));
    if (added.length) setPhotos((prev) => [...prev, ...added]);
  }

  /** Нажатие на фото товара выделяет весь товар, одиночное фото — только себя. */
  function tap(key: string) {
    const id = groupOf[key];
    const keys = id === undefined ? [key] : (groups.find((group) => group.id === id)?.keys ?? [key]);
    setSelected((prev) => {
      const next = new Set(prev);
      const allOn = keys.every((item) => next.has(item));
      for (const item of keys) {
        if (allOn) next.delete(item);
        else next.add(item);
      }
      return next;
    });
  }

  function select(keys: string[]) {
    setSelected(new Set(keys));
  }

  function byPhotoOrder(keys: Iterable<string>) {
    const set = new Set(keys);
    return photos.filter((photo) => set.has(photo.key)).map((photo) => photo.key);
  }

  function splitBy(size: number) {
    const nextGroups: Record<string, number> = {};
    let id = 0;
    photos.forEach((photo, index) => {
      if (index % size === 0) id = nextId();
      nextGroups[photo.key] = id;
    });
    setGroupOf(nextGroups);
    setCatOf({});
    setSelected(new Set());
    setNotice(null);
  }

  function oneProduct() {
    const keys = byPhotoOrder(selected);
    if (keys.length > MAX_PRODUCT_IMAGES) {
      setNotice(`У товара не больше ${MAX_PRODUCT_IMAGES} фото — отметьте меньше.`);
      return;
    }
    const id = nextId();
    const category = selectedGroups.map((group) => catOf[group]).find((item) => item !== undefined);
    setGroupOf((prev) => {
      const next = { ...prev };
      for (const key of keys) next[key] = id;
      return next;
    });
    if (category !== undefined) setCatOf((prev) => ({ ...prev, [id]: category }));
    setSelected(new Set());
    setNotice(null);
  }

  function eachSeparate() {
    const nextGroups = { ...groupOf };
    const nextCats = { ...catOf };
    for (const key of byPhotoOrder(selected)) {
      const old = groupOf[key];
      const id = nextId();
      nextGroups[key] = id;
      const category = old === undefined ? undefined : catOf[old];
      if (category !== undefined) nextCats[id] = category;
    }
    setGroupOf(nextGroups);
    setCatOf(nextCats);
    setSelected(new Set());
    setNotice(null);
  }

  function ungroup() {
    setGroupOf((prev) => {
      const next = { ...prev };
      for (const key of selected) delete next[key];
      return next;
    });
    setSelected(new Set());
  }

  /** Категория отмеченным товарам; одиночные фото становятся отдельными товарами. */
  function assign(category: BatchCategory) {
    const nextGroups = { ...groupOf };
    const nextCats = { ...catOf };
    for (const key of byPhotoOrder(selected)) {
      let id = nextGroups[key];
      if (id === undefined) {
        id = nextId();
        nextGroups[key] = id;
      }
      nextCats[id] = category.id;
    }
    setGroupOf(nextGroups);
    setCatOf(nextCats);
    setSelected(new Set());
    setSheet(false);
  }

  function toggleSize(size: string) {
    setSizes((prev) =>
      prev.includes(size) ? prev.filter((item) => item !== size) : BATCH_SIZES.filter((item) => item === size || prev.includes(item)),
    );
  }

  async function create() {
    const priceKopecks = price.trim() ? parseRublesToKopecks(price) : null;
    if (price.trim() && (priceKopecks === null || priceKopecks <= 0)) {
      setFormError("Цена — например 2490 или 2490,50. Или оставьте поле пустым.");
      return;
    }
    if (uncategorized.length && fallback === null) {
      setFormError("Выберите категорию для товаров без категории.");
      return;
    }
    setFormError(null);
    // Названия — «Категория + №»: номер продолжает счёт товаров категории.
    const counters = new Map(leaf.map((item) => [item.id, item.products_count]));
    const failed: string[] = [];
    let created = 0;
    for (const [index, group] of groups.entries()) {
      const categoryId = group.category !== null && byId.has(group.category) ? group.category : fallback;
      const category = categoryId === null ? undefined : byId.get(categoryId);
      if (!category) continue;
      const number = (counters.get(category.id) ?? 0) + 1;
      counters.set(category.id, number);
      const name = `${category.name} ${number}`;
      setProgress(`Создаю товар ${index + 1} из ${groups.length}…`);
      try {
        const product = await productsService.create({
          name,
          category: category.id,
          price_kopecks: priceKopecks,
          status: status ? Number(status) : null,
          is_draft: true,
          variants: sizes.length ? sizes.map((size) => ({ size, stock })) : undefined,
        });
        created += 1;
        for (const [photoIndex, key] of group.keys.entries()) {
          const photo = photos.find((item) => item.key === key);
          if (!photo) continue;
          setProgress(
            `Товар ${index + 1} из ${groups.length} · фото ${photoIndex + 1} из ${group.keys.length}`,
          );
          try {
            await imagesService.upload(product.id, photo.file);
          } catch {
            failed.push(`${name}: фото ${photo.file.name}`);
          }
        }
      } catch (error) {
        failed.push(`${name}: ${error instanceof ApiError ? error.message : "не создан"}`);
      }
    }
    const result: BatchResult = { created, failed };
    navigate("/catalog/products/drafts", { state: result });
  }

  // --- Отрисовка ---

  const leafCounts = new Map<number, number>();
  for (const group of groups) {
    if (group.category !== null) leafCounts.set(group.category, (leafCounts.get(group.category) ?? 0) + 1);
  }

  const chips: { key: string; label: string; tone?: number | "none"; onClick: () => void }[] = [];
  if (groups.length === 0) {
    chips.push({ key: "q1", label: "Все — по отдельности", onClick: () => splitBy(1) });
    chips.push({ key: "q2", label: "По 2 подряд", onClick: () => splitBy(2) });
    chips.push({ key: "q3", label: "По 3 подряд", onClick: () => splitBy(3) });
  } else {
    for (const category of leaf) {
      const own = groups.filter((group) => group.category === category.id);
      if (!own.length) continue;
      chips.push({
        key: `c${category.id}`,
        label: `${categoryLabel(category, all)} · ${own.length}`,
        tone: category.tone,
        onClick: () => select(own.flatMap((group) => group.keys)),
      });
    }
    if (uncategorized.length) {
      chips.push({
        key: "none",
        label: `Без категории · ${uncategorized.length}`,
        tone: "none",
        onClick: () => select(uncategorized.flatMap((group) => group.keys)),
      });
    }
    if (loose.length) chips.push({ key: "loose", label: `Не в товаре · ${loose.length}`, onClick: () => select(loose) });
  }

  const ready = categories.data && labels.data;
  const statusOptions = [{ id: "", name: "Без статуса" }, ...(labels.data ?? []).map((item) => ({ id: String(item.id), name: item.name }))];

  return (
    <section className="batch">
      <div className="page-header">
        <BackLink to="/catalog/products" label="Товары" />
        <h1>Добавить пачкой</h1>
        {photos.length ? (
          <span className="muted">
            {photos.length} фото · {productsText(groups.length)}
          </span>
        ) : null}
      </div>
      <BatchSteps current={step === "photos" ? 0 : 1} />

      {categories.error || labels.error ? <p className="alert">{categories.error ?? labels.error}</p> : null}
      {notice ? <p className="note note-warning">{notice}</p> : null}
      {!ready ? <p className="muted">Загрузка…</p> : null}

      {ready && step === "photos" && photos.length === 0 ? (
        <div className="batch-empty">
          <label className="batch-drop">
            <span className="batch-drop-icon" aria-hidden="true">
              <Icon name="photos" size={30} />
            </span>
            <strong>Выберите фото из галереи</strong>
            <span className="muted">
              До {MAX_BATCH_PHOTOS} фото за раз, JPEG, PNG или WebP до 5 МБ. Дальше разложите их по товарам.
            </span>
            <span className="button button-accent batch-drop-button">Выбрать фото</span>
            <input className="sr-only" type="file" accept={ACCEPT} multiple onChange={pick} />
          </label>
          <div className="card batch-howto">
            <h2>Как это работает</h2>
            <ol>
              <li>Отметьте фото — по одному, товаром или все сразу — и решите: один товар, каждое отдельно, категория.</li>
              <li>Задайте общее для всех: статус, цену, размеры.</li>
              <li>Поправьте черновики и опубликуйте готовые.</li>
            </ol>
          </div>
        </div>
      ) : null}

      {ready && step === "photos" && photos.length > 0 ? (
        <>
          <div className="batch-toolbar">
            <strong className="batch-toolbar-text" aria-live="polite">
              {selected.size ? `Выбрано: ${plural(selected.size, "фото", "фото", "фото")}` : "Нажмите на фото или товар"}
            </strong>
            {selected.size < photos.length ? (
              <button type="button" className="button button-ghost button-small" onClick={() => select(photos.map((photo) => photo.key))}>
                Выбрать все
              </button>
            ) : null}
            {selected.size ? (
              <button type="button" className="bulk-text" onClick={() => setSelected(new Set())}>
                Снять
              </button>
            ) : null}
          </div>

          <div className="batch-chips" role="group" aria-label={groups.length ? "Выделить группу" : "Разложить все фото"}>
            {chips.map((chip) => (
              <button key={chip.key} type="button" className="batch-chip" onClick={chip.onClick}>
                {chip.tone !== undefined ? (
                  <span className={`cat-dot ${chip.tone === "none" ? "cat-none" : `cat-tone-${chip.tone}`}`} aria-hidden="true" />
                ) : null}
                {chip.label}
              </button>
            ))}
          </div>

          <div className="batch-grid">
            {photos.map((photo, index) => {
              const id = groupOf[photo.key];
              const number = id === undefined ? undefined : groupNumber.get(id);
              const categoryId = id === undefined ? undefined : catOf[id];
              const category = categoryId === undefined ? undefined : byId.get(categoryId);
              const isSelected = selected.has(photo.key);
              const tone = id === undefined ? "" : category ? `cat-tone-${category.tone}` : "cat-none";
              const caption =
                id === undefined
                  ? "не в товаре"
                  : `товар ${number}, ${category ? categoryLabel(category, all) : "без категории"}`;
              return (
                <button
                  key={photo.key}
                  type="button"
                  className={["batch-tile", tone, id !== undefined ? "is-grouped" : "", isSelected ? "is-selected" : ""]
                    .filter(Boolean)
                    .join(" ")}
                  aria-pressed={isSelected}
                  aria-label={`Фото ${index + 1}, ${caption}`}
                  onClick={() => tap(photo.key)}
                >
                  <img src={photo.url} alt="" loading="lazy" />
                  {number !== undefined ? <span className="batch-badge">{number}</span> : null}
                  {isSelected ? (
                    <span className="batch-check" aria-hidden="true">
                      <Icon name="check" size={14} />
                    </span>
                  ) : null}
                </button>
              );
            })}
            {photos.length < MAX_BATCH_PHOTOS ? (
              <label className="batch-add-tile">
                <Icon name="plus" size={24} />
                <span>Ещё фото</span>
                <input className="sr-only" type="file" accept={ACCEPT} multiple onChange={pick} />
              </label>
            ) : null}
          </div>

          {selected.size ? (
            <div className="batch-dock batch-actions" role="region" aria-label="Действия с отмеченными фото">
              <span className="batch-actions-hint">
                {[selectedGroups.length ? productsText(selectedGroups.length) : "", selectedLoose ? `${selectedLoose} фото не в товаре` : ""]
                  .filter(Boolean)
                  .join(" и ")}
              </span>
              <div className="batch-actions-grid">
                <button type="button" className="batch-action is-primary" onClick={oneProduct}>
                  <Icon name="merge" />
                  Один товар
                </button>
                <button type="button" className="batch-action" onClick={eachSeparate}>
                  <Icon name="split" />
                  Каждое отдельно
                </button>
                <button type="button" className="batch-action" onClick={() => setSheet(true)}>
                  <Icon name="folder" />
                  Категория
                </button>
                <button type="button" className="batch-action" disabled={!selectedGroups.length} onClick={ungroup}>
                  <Icon name="ungroup" />
                  Разобрать
                </button>
              </div>
            </div>
          ) : (
            <div className="batch-dock batch-next">
              <span className="muted small">
                {groups.length === 0
                  ? "Отметьте фото или выберите способ разложить все"
                  : loose.length
                    ? `Не в товаре: ${loose.length} фото — они не войдут`
                    : "Все фото разложены по товарам"}
              </span>
              <button
                type="button"
                className="button button-accent batch-cta"
                disabled={!groups.length}
                onClick={() => {
                  setStep("common");
                  window.scrollTo({ top: 0 });
                }}
              >
                {groups.length ? `Дальше · ${productsText(groups.length)}` : "Дальше"}
              </button>
            </div>
          )}
        </>
      ) : null}

      {ready && step === "common" ? (
        <div className="batch-common">
          <section className="card batch-field">
            <h2>Категории</h2>
            <div className="batch-summary">
              {leaf
                .filter((category) => leafCounts.get(category.id))
                .map((category) => (
                  <span key={category.id} className="batch-summary-item">
                    <span className={`cat-dot cat-tone-${category.tone}`} aria-hidden="true" />
                    {categoryLabel(category, all)} · {leafCounts.get(category.id)}
                  </span>
                ))}
              {uncategorized.length ? (
                <span className="batch-summary-item is-warning">
                  <span className="cat-dot cat-none" aria-hidden="true" />
                  Без категории · {uncategorized.length}
                </span>
              ) : null}
            </div>
            {uncategorized.length ? (
              <>
                <p className="batch-label">Без категории ({uncategorized.length}) — в какую?</p>
                <div className="batch-options" role="radiogroup" aria-label="Категория для остальных">
                  {leaf.map((category) => (
                    <button
                      key={category.id}
                      type="button"
                      role="radio"
                      aria-checked={fallback === category.id}
                      className="batch-option"
                      onClick={() => setFallback(category.id)}
                    >
                      {categoryLabel(category, all)}
                    </button>
                  ))}
                </div>
              </>
            ) : null}
            <p className="muted small">Названия — «Категория + №», поправите в карточке черновика.</p>
          </section>

          <section className="card batch-field">
            <h2>Статус</h2>
            <div className="batch-options" role="radiogroup" aria-label="Статус">
              {statusOptions.map((item) => (
                <button
                  key={item.id || "none"}
                  type="button"
                  role="radio"
                  aria-checked={status === item.id}
                  className="batch-option"
                  onClick={() => setStatus(item.id)}
                >
                  {item.name}
                </button>
              ))}
            </div>
          </section>

          <section className="card batch-field">
            <h2>
              <label htmlFor="batch-price">Цена для всех</label>
            </h2>
            <span className="money">
              <input
                id="batch-price"
                inputMode="decimal"
                value={price}
                placeholder="Можно оставить пустой"
                onChange={(event) => setPrice(event.target.value)}
              />
              <span>₽</span>
            </span>
            <p className="muted small">Без цены черновик помечается «Нет цены» — впишете в карточке или сразу нескольким.</p>
          </section>

          <section className="card batch-field">
            <h2>Размеры</h2>
            <div className="batch-options" role="group" aria-label="Размеры">
              {BATCH_SIZES.map((size) => (
                <button
                  key={size}
                  type="button"
                  aria-pressed={sizes.includes(size)}
                  className="batch-option"
                  onClick={() => toggleSize(size)}
                >
                  {size}
                </button>
              ))}
            </div>
            <div className="batch-stock">
              <span>Остаток каждого размера</span>
              <span className="batch-stepper">
                <button type="button" aria-label="Меньше" disabled={stock === 0} onClick={() => setStock((n) => Math.max(0, n - 1))}>
                  −
                </button>
                <output aria-live="polite">{stock}</output>
                <button type="button" aria-label="Больше" onClick={() => setStock((n) => n + 1)}>
                  +
                </button>
              </span>
            </div>
            <p className="muted small">
              {sizes.length
                ? "0 публикации не мешает: товар будет «нет в наличии», пока не впишете остаток."
                : "Без размеров — один вариант «Без размера»."}
            </p>
          </section>

          {formError ? <p className="alert">{formError}</p> : null}

          <div className="batch-dock batch-next">
            {progress ? (
              <span className="batch-progress" role="status">
                {progress}
              </span>
            ) : null}
            <div className="batch-next-row">
              <button
                type="button"
                className="button button-ghost batch-back"
                disabled={progress !== null}
                onClick={() => {
                  setStep("photos");
                  window.scrollTo({ top: 0 });
                }}
              >
                <Icon name="left" size={18} /> Фото
              </button>
              <button type="button" className="button button-accent batch-cta" disabled={progress !== null} onClick={() => void create()}>
                {progress ? "Создаю черновики…" : `Создать ${plural(groups.length, "черновик", "черновика", "черновиков")}`}
              </button>
            </div>
          </div>
        </div>
      ) : null}

      {sheet ? (
        <CategorySheet
          title={`Категория · ${productsText(selectedGroups.length + selectedLoose)}`}
          note={selectedLoose ? `Фото не в товаре (${selectedLoose}) станут отдельными товарами.` : undefined}
          categories={leaf}
          all={all}
          counts={leafCounts}
          onPick={assign}
          onClose={() => setSheet(false)}
        />
      ) : null}

      {ready && leaf.length === 0 ? (
        <p className="note note-warning">
          Нет категорий для товаров. <Link to="/catalog/categories">Создайте категорию</Link>, чтобы раскладывать товары.
        </p>
      ) : null}
    </section>
  );
}
