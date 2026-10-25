import { type FormEvent, useState } from "react";

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

function FieldError({ errors, name }: { errors: FieldErrors; name: string }) {
  const message = errors[name]?.[0];
  return message ? <span className="field-error">{message}</span> : null;
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
  const [sizes, setSizes] = useState("");
  const [errors, setErrors] = useState<FieldErrors>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    const priceKopecks = onRequest ? null : parseRublesToKopecks(price);
    const compareKopecks = !onRequest && compareAt.trim() ? parseRublesToKopecks(compareAt) : null;
    const local: FieldErrors = {};
    if (!onRequest && (priceKopecks === null || priceKopecks <= 0)) {
      local.price_kopecks = ["Введите цену, например 1990 или 1990,50."];
    }
    if (!onRequest && compareAt.trim() && compareKopecks === null)
      local.compare_at_kopecks = ["Неверный формат суммы."];
    if (!category) local.category = ["Выберите категорию."];
    setErrors(local);
    setFormError(null);
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
        sizes: sizes
          .split(",")
          .map((size) => size.trim())
          .filter(Boolean),
      });
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

  return (
    <form className="card form-grid" onSubmit={submit}>
      {formError ? <p className="alert">{formError}</p> : null}

      <label className="field">
        Название
        <input value={name} maxLength={200} required onChange={(e) => setName(e.target.value)} />
        <FieldError errors={errors} name="name" />
      </label>

      <label className="field">
        Адрес (slug)
        <input
          value={slug}
          maxLength={220}
          placeholder={product ? undefined : "Сгенерируется из названия"}
          onChange={(e) => setSlug(e.target.value)}
        />
        <FieldError errors={errors} name="slug" />
      </label>

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

      <label className="checkbox">
        <input type="checkbox" checked={onRequest} onChange={(e) => setOnRequest(e.target.checked)} />
        Цена по запросу — вместо цены и корзины кнопка «Узнать»
      </label>

      {onRequest ? null : (
        <div className="form-row">
          <label className="field">
            Цена, ₽
            <input inputMode="decimal" value={price} onChange={(e) => setPrice(e.target.value)} />
            <FieldError errors={errors} name="price_kopecks" />
          </label>
          <label className="field">
            Старая цена, ₽
            <input
              inputMode="decimal"
              value={compareAt}
              placeholder="Без скидки"
              onChange={(e) => setCompareAt(e.target.value)}
            />
            <FieldError errors={errors} name="compare_at_kopecks" />
          </label>
        </div>
      )}

      <label className="field">
        Описание
        <textarea rows={5} value={description} onChange={(e) => setDescription(e.target.value)} />
      </label>

      {product ? null : (
        <label className="field">
          Размеры через запятую
          <input
            value={sizes}
            placeholder="Пусто — товар без размера (S, M, L или 40, 41, 42)"
            onChange={(e) => setSizes(e.target.value)}
          />
          <span className="muted">Остатки и артикулы задаются после создания.</span>
          <FieldError errors={errors} name="variants" />
        </label>
      )}

      <label className="checkbox">
        <input type="checkbox" checked={isActive} onChange={(e) => setIsActive(e.target.checked)} />
        Показывать на витрине
      </label>

      <div>
        <button type="submit" className="button" disabled={saving}>
          {saving ? "Сохранение…" : product ? "Сохранить" : "Создать товар"}
        </button>
      </div>
    </form>
  );
}
