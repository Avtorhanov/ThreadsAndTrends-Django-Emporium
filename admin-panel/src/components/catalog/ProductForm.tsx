import { type FormEvent, type KeyboardEvent, useState } from "react";

import type { Category, Product, ProductCreate } from "../../api/catalog";
import { ApiError, type FieldErrors } from "../../api/errors";
import { isLeaf, sortCategoryTree } from "../../hooks/useCatalog";
import { kopecksToInput, parseRublesToKopecks } from "../../lib/money";

export type ProductFormValues = Omit<ProductCreate, "variants"> & { sizes: string[] };

type Props = {
  product: Product | null;
  categories: Category[];
  onSubmit: (values: ProductFormValues) => Promise<void>;
};

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

export function ProductForm({ product, categories, onSubmit }: Props) {
  const [name, setName] = useState(product?.name ?? "");
  const [slug, setSlug] = useState(product?.slug ?? "");
  const [category, setCategory] = useState(product ? String(product.category) : "");
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

  async function submit(event: FormEvent) {
    event.preventDefault();
    const priceKopecks = onRequest ? null : parseRublesToKopecks(price);
    const compareKopecks = !onRequest && compareAt.trim() ? parseRublesToKopecks(compareAt) : null;
    const local: FieldErrors = {};
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
    if (Object.keys(local).length > 0) return;

    setSaving(true);
    try {
      await onSubmit({
        name: name.trim(),
        slug: slug.trim(),
        category: Number(category),
        price_kopecks: priceKopecks,
        compare_at_kopecks: compareKopecks,
        description,
        is_active: isActive,
        sizes,
      });
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
    <form className="card pf" onSubmit={submit}>
      {formError ? <p className="alert pf-wide">{formError}</p> : null}

      <div className="pf-main">
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

        <label className="field">
          <span className="field-head">
            Описание
            {description.length ? (
              <span className="muted">
                {description.length} симв.{paragraphs > 1 ? ` · абзацев: ${paragraphs}` : ""}
              </span>
            ) : null}
          </span>
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

        {product ? null : (
          <div className="field">
            Размеры
            <SizesInput sizes={sizes} onChange={setSizes} />
            <span className="muted">Остатки и артикулы — после создания, в блоке «Варианты и остатки».</span>
            <FieldError errors={errors} name="variants" />
          </div>
        )}
      </div>

      <aside className="pf-side">
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

        <div className="field">
          Цена
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
              <label className="money">
                <input
                  inputMode="decimal"
                  value={price}
                  placeholder="Цена"
                  aria-label="Цена, ₽"
                  onChange={(e) => setPrice(e.target.value)}
                />
                <span>₽</span>
              </label>
              <label className="money">
                <input
                  inputMode="decimal"
                  value={compareAt}
                  placeholder="Старая"
                  aria-label="Старая цена, ₽ (необязательно)"
                  onChange={(e) => setCompareAt(e.target.value)}
                />
                <span>₽</span>
              </label>
            </div>
          )}
          <FieldError errors={errors} name="price_kopecks" />
          <FieldError errors={errors} name="compare_at_kopecks" />
        </div>

        <label className="switch">
          <input type="checkbox" checked={isActive} onChange={(e) => setIsActive(e.target.checked)} />
          <span className="switch-track" aria-hidden="true" />
          Показывать на витрине
        </label>

        <details className="pf-more">
          <summary>Дополнительно</summary>
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

        <div className="pf-actions">
          <button type="submit" className="button" disabled={saving}>
            {saving ? "Сохранение…" : product ? "Сохранить" : "Создать товар"}
          </button>
          {saved && !saving ? <span className="saved">Сохранено</span> : null}
        </div>
      </aside>
    </form>
  );
}
