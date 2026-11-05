import { type KeyboardEvent, type ReactNode, useEffect, useState } from "react";

import type { Category, Product, ProductCreate, ProductLabel } from "../../api/catalog";
import { ApiError, type FieldErrors } from "../../api/errors";
import { isLeaf, sortCategoryTree } from "../../hooks/useCatalog";
import { kopecksToInput, parseRublesToKopecks } from "../../lib/money";

export type ProductFormValues = Omit<ProductCreate, "variants"> & { sizes: string[] };

type Props = {
  product: Product | null;
  categories: Category[];
  labels: ProductLabel[];
  /** Группа «Фото»: галерея товара или фото, выбранные до создания. */
  photos: ReactNode;
  /** Остатки и артикулы существующего товара (группа «Цена и наличие»). */
  stock: ReactNode;
  /** Есть выбранные, но ещё не загруженные фото — это тоже несохранённое. */
  extraDirty?: boolean;
  onSubmit: (values: ProductFormValues) => Promise<void>;
};

function Group({ number, title, aside, children }: { number: number; title: string; aside?: ReactNode; children: ReactNode }) {
  return (
    <section className="card pf-group" aria-label={title}>
      <div className="pf-group-head">
        <span className="pf-num" aria-hidden="true">
          {number}
        </span>
        <h2>{title}</h2>
        {aside ? <span className="pf-group-aside">{aside}</span> : null}
      </div>
      {children}
    </section>
  );
}

// Готовые наборы размеров: одним нажатием, потом можно убрать лишние.
const SIZE_PRESETS: { label: string; sizes: string[] }[] = [
  { label: "Одежда", sizes: ["XS", "S", "M", "L", "XL"] },
  { label: "Обувь", sizes: ["36", "37", "38", "39", "40", "41", "42", "43", "44"] },
  { label: "Дети, рост", sizes: ["116", "122", "128", "134", "140", "146", "152", "158", "164"] },
];

function FieldError({ errors, name }: { errors: FieldErrors; name: string }) {
  const message = errors[name]?.[0];
  return message ? <span className="field-error">{message}</span> : null;
}

/** Размеры чипами: Enter или запятая — добавить, × — убрать. Пусто — товар без размера. */
function SizesInput({ sizes, onChange }: { sizes: string[]; onChange: (sizes: string[]) => void }) {
  const [draft, setDraft] = useState("");
  const add = (values: string[]) => {
    const next = [...sizes];
    for (const raw of values) {
      const value = raw.trim();
      if (value && !next.includes(value)) next.push(value);
    }
    onChange(next);
  };
  const commit = () => {
    if (!draft.trim()) return;
    add(draft.split(","));
    setDraft("");
  };
  const onKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "Enter" || event.key === ",") {
      event.preventDefault();
      commit();
    } else if (event.key === "Backspace" && !draft && sizes.length) {
      onChange(sizes.slice(0, -1));
    }
  };
  return (
    <div className="pf-sizes">
      <div className="chips">
        {sizes.map((size) => (
          <span className="chip" key={size}>
            {size}
            <button
              type="button"
              className="chip-x"
              aria-label={`Убрать размер ${size}`}
              onClick={() => onChange(sizes.filter((s) => s !== size))}
            >
              ×
            </button>
          </span>
        ))}
        <input
          value={draft}
          maxLength={50}
          aria-label="Добавить размер"
          placeholder={sizes.length ? "Ещё размер" : "Без размера — или введите S, M… и Enter"}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={onKeyDown}
          onBlur={commit}
        />
      </div>
      <div className="presets">
        {SIZE_PRESETS.map((preset) => (
          <button key={preset.label} type="button" className="preset" onClick={() => add(preset.sizes)}>
            + {preset.label}
          </button>
        ))}
        {sizes.length ? (
          <button type="button" className="preset preset-clear" onClick={() => onChange([])}>
            Очистить
          </button>
        ) : null}
      </div>
    </div>
  );
}

export function ProductForm({ product, categories, labels, photos, stock, extraDirty = false, onSubmit }: Props) {
  const [name, setName] = useState(product?.name ?? "");
  const [slug, setSlug] = useState(product?.slug ?? "");
  const [category, setCategory] = useState(product ? String(product.category) : "");
  const [status, setStatus] = useState(product?.status ? String(product.status) : "");
  const [price, setPrice] = useState(kopecksToInput(product?.price_kopecks));
  // Цена по запросу: на витрине вместо цены и корзины — «Узнать» (мессенджеры магазина).
  const [onRequest, setOnRequest] = useState(product ? product.price_kopecks === null : false);
  const [compareAt, setCompareAt] = useState(kopecksToInput(product?.compare_at_kopecks));
  const [description, setDescription] = useState(product?.description ?? "");
  const [isActive, setIsActive] = useState(product?.is_active ?? true);
  const [sizes, setSizes] = useState<string[]>([]);
  const [errors, setErrors] = useState<FieldErrors>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  // Несохранённые изменения: сравнение с тем, что пришло с сервера.
  const snapshot = JSON.stringify([name, slug, category, status, price, onRequest, compareAt, description, isActive, sizes]);
  const [initial] = useState(snapshot);
  const dirty = !saving && (snapshot !== initial || extraDirty);
  useEffect(() => {
    if (!dirty) return;
    const warn = (event: BeforeUnloadEvent) => event.preventDefault();
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [dirty]);

  async function submit(event: { preventDefault: () => void }, publish?: boolean) {
    event.preventDefault();
    const priceKopecks = onRequest ? null : parseRublesToKopecks(price);
    const compareKopecks = !onRequest && compareAt.trim() ? parseRublesToKopecks(compareAt) : null;
    const local: FieldErrors = {};
    if (!name.trim()) local.name = ["Введите название."];
    if (!onRequest && (priceKopecks === null || priceKopecks <= 0)) {
      local.price_kopecks = ["Введите цену, например 1990 или 1990,50."];
    }
    if (!onRequest && compareAt.trim() && compareKopecks === null) {
      local.compare_at_kopecks = ["Неверный формат суммы."];
    }
    if (!category) local.category = ["Выберите категорию."];
    setErrors(local);
    setFormError(null);
    setSaved(false);
    if (Object.keys(local).length > 0) {
      setFormError("Проверьте отмеченные поля.");
      return;
    }

    const active = publish === undefined ? isActive : publish;
    setSaving(true);
    try {
      await onSubmit({
        name: name.trim(),
        slug: slug.trim(),
        category: Number(category),
        status: status ? Number(status) : null,
        price_kopecks: priceKopecks,
        compare_at_kopecks: compareKopecks,
        description,
        is_active: active,
        sizes,
      });
      setIsActive(active);
      setSaved(true);
    } catch (err) {
      if (err instanceof ApiError) {
        setErrors(err.fieldErrors);
        setFormError(err.message);
      } else {
        setFormError("Не удалось сохранить товар.");
      }
    } finally {
      setSaving(false);
    }
  }

  const options = sortCategoryTree(categories);
  const paragraphs = description.split(/\n\s*\n/).filter((p) => p.trim()).length;

  return (
    <form className="pf-form" onSubmit={(event) => void submit(event)} noValidate>
      <div className="pf-bar">
        {dirty ? (
          <span className="unsaved" role="status">
            Есть несохранённые изменения
          </span>
        ) : saved ? (
          <span className="saved" role="status">
            {product ? "Сохранено" : "Товар создан"}
          </span>
        ) : (
          <span className="muted small">
            {product ? "Изменений нет" : "Заполните группы 1–4 и опубликуйте товар или сохраните скрытым"}
          </span>
        )}
        <span className="pf-bar-gap" />
        {product ? (
          <button type="submit" className="button" disabled={saving}>
            {saving ? "Сохранение…" : "Сохранить"}
          </button>
        ) : (
          <>
            <button
              type="button"
              className="button button-ghost"
              disabled={saving}
              onClick={(event) => void submit(event, false)}
            >
              Сохранить скрытым
            </button>
            <button
              type="button"
              className="button"
              disabled={saving}
              onClick={(event) => void submit(event, true)}
            >
              {saving ? "Сохранение…" : "Опубликовать"}
            </button>
          </>
        )}
      </div>
      {formError ? <p className="alert">{formError}</p> : null}

      <div className="pf-groups">
        <Group number={1} title="Основное">
          <label className="field">
            Название
            <input
              className="pf-title"
              value={name}
              maxLength={200}
              required
              placeholder="Бренд — что это, например «Stanley — термобутылка 473 мл»"
              onChange={(e) => setName(e.target.value)}
            />
            <FieldError errors={errors} name="name" />
          </label>
          <div className="pf-prices">
            <label className="field">
              Категория
              <select value={category} onChange={(e) => setCategory(e.target.value)}>
                <option value="">Выберите…</option>
                {options.map((item) => (
                  <option key={item.id} value={item.id} disabled={!isLeaf(item)}>
                    {item.depth ? `— ${item.name}` : item.name}
                  </option>
                ))}
              </select>
              <FieldError errors={errors} name="category" />
            </label>
            <label className="field">
              Статус
              <select value={status} onChange={(e) => setStatus(e.target.value)}>
                <option value="">Без статуса</option>
                {labels.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.name}
                  </option>
                ))}
              </select>
              <FieldError errors={errors} name="status" />
            </label>
          </div>
          {product ? (
            <label className="switch">
              <input type="checkbox" checked={isActive} onChange={(e) => setIsActive(e.target.checked)} />
              <span className="switch-track" aria-hidden="true" />
              Показывать на витрине
            </label>
          ) : null}
        </Group>

        <Group number={2} title="Фото">
          <div className="pf-embed">{photos}</div>
        </Group>

        <Group number={3} title="Цена и наличие">
          <div className="seg-switch" role="radiogroup" aria-label="Цена">
            <button
              type="button"
              role="radio"
              aria-checked={!onRequest}
              className={onRequest ? "" : "is-on"}
              onClick={() => setOnRequest(false)}
            >
              В рублях
            </button>
            <button
              type="button"
              role="radio"
              aria-checked={onRequest}
              className={onRequest ? "is-on" : ""}
              onClick={() => setOnRequest(true)}
            >
              По запросу
            </button>
          </div>
          {onRequest ? (
            <span className="muted">На витрине вместо цены и корзины — кнопка «Узнать» с мессенджерами магазина.</span>
          ) : (
            <div className="pf-prices">
              <label className="field">
                Цена
                <span className="money">
                  <input inputMode="decimal" value={price} aria-label="Цена, ₽" onChange={(e) => setPrice(e.target.value)} />
                  <span>₽</span>
                </span>
              </label>
              <label className="field">
                Старая цена
                <span className="money">
                  <input
                    inputMode="decimal"
                    value={compareAt}
                    placeholder="необязательно"
                    aria-label="Старая цена, ₽"
                    onChange={(e) => setCompareAt(e.target.value)}
                  />
                  <span>₽</span>
                </span>
              </label>
            </div>
          )}
          <FieldError errors={errors} name="price_kopecks" />
          <FieldError errors={errors} name="compare_at_kopecks" />
          {product ? (
            <div className="pf-embed">{stock}</div>
          ) : (
            <div className="field">
              Размеры
              <SizesInput sizes={sizes} onChange={setSizes} />
              <span className="muted">Остатки и артикулы — после сохранения, здесь же.</span>
              <FieldError errors={errors} name="variants" />
            </div>
          )}
        </Group>

        <Group
          number={4}
          title="Описание"
          aside={
            description.length ? (
              <>
                {description.length} симв.{paragraphs > 1 ? ` · абзацев: ${paragraphs}` : ""}
              </>
            ) : null
          }
        >
          <label className="field">
            <span className="sr-only">Описание</span>
            <textarea
              className="pf-desc"
              rows={8}
              value={description}
              placeholder={
                "Что это и чем хорошо: материал, размеры, цвета на выбор, откуда и сроки.\n\nАбзацы — через пустую строку."
              }
              onChange={(e) => setDescription(e.target.value)}
            />
            <FieldError errors={errors} name="description" />
          </label>
          <details className="pf-more">
            <summary>Дополнительно: адрес страницы</summary>
            <label className="field">
              Адрес на сайте (slug)
              <input
                value={slug}
                maxLength={220}
                placeholder={product ? undefined : "Сгенерируется из названия"}
                onChange={(e) => setSlug(e.target.value)}
              />
              <FieldError errors={errors} name="slug" />
            </label>
          </details>
        </Group>
      </div>
    </form>
  );
}
