import { type ChangeEvent, useEffect, useState } from "react";

import { type Category, type ProductRow, productsService } from "../../api/catalog";
import {
  BANNER_TONES,
  type CollectionSource,
  HOME_LIMITS,
  type HomeBlock,
  type HomeBlockChanges,
  SOURCE_LABELS,
} from "../../api/home";
import { sortCategoryTree } from "../../hooks/useCatalog";
import { useDebouncedValue } from "../../hooks/useDebouncedValue";
import { formatKopecks } from "../../lib/money";

const HEADINGS: Record<HomeBlock["kind"], string> = {
  banner: "Баннер",
  collection: "Подборка товаров",
  categories: "Лента категорий",
  text: "Текстовый блок",
};

type Props = {
  block: HomeBlock;
  categories: Category[];
  error: string | null;
  busy: boolean;
  /** delay — пауза перед сохранением: текст копится, выбор из списка сохраняется сразу. */
  onChange: (changes: HomeBlockChanges, delay?: number) => void;
  onUpload: (file: File) => void;
  onRemoveImage: () => void;
  onDelete: () => void;
  onBack: () => void;
};

function Counter({ value, max }: { value: string; max: number }) {
  return (
    <span className={value.length > max ? "field-error small" : "muted small"}>
      {value.length} / {max}
    </span>
  );
}

/** Настройки выбранного блока. Правки сохраняются в черновик сами — покупатель их не видит. */
export function BlockSettings(props: Props) {
  const { block, categories, error, busy, onChange, onDelete, onBack } = props;
  const [confirming, setConfirming] = useState(false);
  const tree = sortCategoryTree(categories);
  useEffect(() => setConfirming(false), [block.id]);

  return (
    <div className="card he-settings-card">
      <div className="he-settings-head">
        <button type="button" className="button button-ghost he-phone-only" onClick={onBack}>
          ← Все блоки
        </button>
        <h2>{HEADINGS[block.kind]}</h2>
        <label className="check he-visible">
          <input
            type="checkbox"
            checked={block.is_visible}
            onChange={(event) => onChange({ is_visible: event.target.checked }, 0)}
          />
          Показывать
        </label>
      </div>
      {error ? <p className="alert">Не сохранено: {error}</p> : null}

      {block.kind === "categories" ? (
        <p className="muted">
          Показывает активные категории в порядке из раздела «Категории». Здесь — только заголовок, место на
          странице и видимость.
        </p>
      ) : null}

      <label className="field">
        <span className="field-head">
          Заголовок <Counter value={block.title} max={HOME_LIMITS.title} />
        </span>
        <input
          value={block.title}
          maxLength={HOME_LIMITS.title}
          placeholder={block.kind === "collection" ? "Например: Новинки" : ""}
          onChange={(event) => onChange({ title: event.target.value })}
        />
      </label>

      {block.kind === "banner" ? <BannerFields {...props} tree={tree} /> : null}
      {block.kind === "collection" ? <CollectionFields {...props} tree={tree} /> : null}
      {block.kind === "text" ? (
        <label className="field">
          <span className="field-head">
            Текст <Counter value={block.text} max={HOME_LIMITS.text} />
          </span>
          <textarea
            rows={7}
            value={block.text}
            maxLength={HOME_LIMITS.text}
            placeholder="Пустая строка — новый абзац"
            onChange={(event) => onChange({ text: event.target.value })}
          />
        </label>
      ) : null}

      <div className="he-delete">
        {confirming ? (
          <div className="he-confirm" role="alertdialog" aria-label="Удаление блока">
            <span>
              Удалить блок «{block.title || HEADINGS[block.kind]}»? Его можно будет добавить заново.
            </span>
            <div className="status-actions">
              <button type="button" className="button button-ghost" onClick={() => setConfirming(false)}>
                Отмена
              </button>
              <button type="button" className="button button-danger" disabled={busy} onClick={onDelete}>
                Удалить
              </button>
            </div>
          </div>
        ) : (
          <button type="button" className="button button-ghost he-delete-btn" onClick={() => setConfirming(true)}>
            Удалить блок
          </button>
        )}
      </div>
    </div>
  );
}

type TreeProps = Props & { tree: Array<Category & { depth: number }> };

function CategorySelect({
  value,
  tree,
  empty,
  onSelect,
}: {
  value: number | null;
  tree: TreeProps["tree"];
  empty?: string;
  onSelect: (id: number | null) => void;
}) {
  return (
    <select value={value ?? ""} onChange={(event) => onSelect(event.target.value ? Number(event.target.value) : null)}>
      {empty ? <option value="">{empty}</option> : null}
      {tree.map((item) => (
        <option key={item.id} value={item.id}>
          {item.depth ? `— ${item.name}` : item.name}
          {item.is_active ? "" : " (скрыта)"}
        </option>
      ))}
    </select>
  );
}

function BannerFields({ block, tree, busy, onChange, onUpload, onRemoveImage }: TreeProps) {
  const custom = !BANNER_TONES.some((tone) => tone.color === block.color.toUpperCase());

  function pick(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (file) onUpload(file);
  }

  return (
    <>
      <div className="field">
        <span>Цвет</span>
        <div className="he-tones" role="radiogroup" aria-label="Цвет баннера">
          {BANNER_TONES.map((tone) => (
            <button
              key={tone.color}
              type="button"
              role="radio"
              aria-checked={block.color.toUpperCase() === tone.color}
              className="he-tone"
              style={{ background: tone.color }}
              title={tone.label}
              onClick={() => onChange({ color: tone.color }, 0)}
            >
              <span className="sr-only">{tone.label}</span>
            </button>
          ))}
          <label className={custom ? "he-tone he-tone-custom is-on" : "he-tone he-tone-custom"} title="Свой цвет">
            <input
              type="color"
              value={/^#[0-9a-f]{6}$/i.test(block.color) ? block.color : "#FFE38F"}
              onChange={(event) => onChange({ color: event.target.value.toUpperCase() })}
            />
            Свой
          </label>
        </div>
        <span className="muted small">Цвет текста на баннере подбирается сам — чтобы читалось.</span>
      </div>

      <label className="field">
        <span className="field-head">
          Короткое описание <Counter value={block.text} max={HOME_LIMITS.bannerText} />
        </span>
        <textarea
          rows={2}
          value={block.text}
          maxLength={HOME_LIMITS.bannerText}
          onChange={(event) => onChange({ text: event.target.value })}
        />
      </label>

      <div className="field">
        <span>Изображение</span>
        {block.image_url ? (
          <div className="he-image">
            <img src={block.image_url} alt="" />
            <div className="status-actions">
              <label className="button button-outline">
                Заменить
                <input type="file" accept="image/jpeg,image/png,image/webp" hidden disabled={busy} onChange={pick} />
              </label>
              <button type="button" className="button button-ghost" disabled={busy} onClick={onRemoveImage}>
                Убрать
              </button>
            </div>
          </div>
        ) : (
          <label className="drop-zone">
            <strong>Выбрать картинку</strong>
            <span className="muted small">JPEG, PNG или WebP до 5 МБ · справа от текста</span>
            <input type="file" accept="image/jpeg,image/png,image/webp" hidden disabled={busy} onChange={pick} />
          </label>
        )}
      </div>

      <label className="field">
        <span>Переход по нажатию</span>
        <CategorySelect
          value={block.category}
          tree={tree}
          empty="Без перехода"
          onSelect={(category) => onChange({ category }, 0)}
        />
      </label>
    </>
  );
}

function CollectionFields({ block, tree, onChange }: TreeProps) {
  const sources = Object.entries(SOURCE_LABELS) as [CollectionSource, string][];

  function setSource(source: CollectionSource) {
    if (source === "category" && block.category === null) {
      const first = tree[0];
      if (!first) return;
      onChange({ source, category: first.id }, 0);
      return;
    }
    onChange({ source }, 0);
  }

  return (
    <>
      <div className="field">
        <span>Какие товары</span>
        <div className="seg-switch he-sources" role="radiogroup" aria-label="Какие товары">
          {sources.map(([value, label]) => (
            <button
              key={value}
              type="button"
              role="radio"
              aria-checked={block.source === value}
              className={block.source === value ? "is-on" : undefined}
              onClick={() => setSource(value)}
            >
              {label}
            </button>
          ))}
        </div>
      </div>
      {block.source === "category" ? (
        <label className="field">
          <span>Категория</span>
          <CategorySelect value={block.category} tree={tree} onSelect={(category) => onChange({ category }, 0)} />
        </label>
      ) : null}
      {block.source === "manual" ? <ManualProducts block={block} onChange={onChange} /> : null}
      <p className="muted small">
        {block.source === "manual"
          ? `До ${HOME_LIMITS.manualProducts} товаров в выбранном порядке.`
          : "До 8 товаров, сначала новые."}{" "}
        Скрытые и удалённые товары в подборку не попадают — она обновляется сама.
      </p>
    </>
  );
}

function ManualProducts({ block, onChange }: Pick<Props, "block" | "onChange">) {
  const [search, setSearch] = useState("");
  const [results, setResults] = useState<ProductRow[]>([]);
  const query = useDebouncedValue(search.trim());
  const ids = block.product_ids;
  const shown = new Map(block.preview_products.map((product) => [product.id, product]));
  const [names, setNames] = useState<Map<number, string>>(new Map());

  useEffect(() => {
    let cancelled = false;
    if (!query) {
      setResults([]);
      return;
    }
    productsService
      .list({ search: query, status: "active", label: "", category: null, stock: "", page: 1 })
      .then((page) => !cancelled && setResults(page.results.slice(0, 8)))
      .catch(() => !cancelled && setResults([]));
    return () => {
      cancelled = true;
    };
  }, [query]);

  function add(product: ProductRow) {
    if (ids.includes(product.id) || ids.length >= HOME_LIMITS.manualProducts) return;
    setNames((prev) => new Map(prev).set(product.id, product.name));
    onChange({ product_ids: [...ids, product.id] }, 0);
  }

  function move(index: number, delta: number) {
    const next = [...ids];
    const [id] = next.splice(index, 1);
    if (id === undefined) return;
    next.splice(index + delta, 0, id);
    onChange({ product_ids: next }, 0);
  }

  return (
    <div className="field">
      <span className="field-head">
        Товары подборки
        <span className="muted small">
          {ids.length} из {HOME_LIMITS.manualProducts}
        </span>
      </span>
      {ids.length ? (
        <ol className="he-picked">
          {ids.map((id, index) => {
            const product = shown.get(id);
            return (
              <li key={id}>
                <span className={product ? undefined : "muted"}>
                  {product?.name ?? names.get(id) ?? `Товар #${id}`}
                  {product ? "" : " — скрыт, покупатель не увидит"}
                </span>
                <button type="button" aria-label="Выше" disabled={index === 0} onClick={() => move(index, -1)}>
                  ↑
                </button>
                <button
                  type="button"
                  aria-label="Ниже"
                  disabled={index === ids.length - 1}
                  onClick={() => move(index, 1)}
                >
                  ↓
                </button>
                <button
                  type="button"
                  aria-label="Убрать из подборки"
                  onClick={() => onChange({ product_ids: ids.filter((item) => item !== id) }, 0)}
                >
                  ×
                </button>
              </li>
            );
          })}
        </ol>
      ) : null}
      <input
        type="search"
        value={search}
        placeholder="Найти товар по названию или артикулу"
        onChange={(event) => setSearch(event.target.value)}
      />
      {results.length ? (
        <ul className="he-results">
          {results.map((product) => (
            <li key={product.id}>
              {product.cover_url ? <img className="thumb" src={product.cover_url} alt="" /> : <span className="thumb thumb-empty" />}
              <span>
                {product.name}
                <span className="muted small">
                  {" "}
                  · {product.price_kopecks === null ? "по запросу" : formatKopecks(product.price_kopecks)}
                </span>
              </span>
              <button
                type="button"
                className="button button-outline"
                disabled={ids.includes(product.id) || ids.length >= HOME_LIMITS.manualProducts}
                onClick={() => add(product)}
              >
                {ids.includes(product.id) ? "Добавлен" : "Добавить"}
              </button>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
