import { useEffect, useState } from "react";
import { Link } from "react-router";

import {
  PRODUCTS_PAGE_SIZE,
  type ProductBulk,
  type ProductRow,
  type ProductStatus,
  type StockFilter,
  productsService,
} from "../api/catalog";
import { ApiError } from "../api/errors";
import { batchCategories } from "../components/catalog/batch";
import { CategorySheet } from "../components/catalog/CategorySheet";
import { ColorLinkSheet } from "../components/catalog/ColorLinkSheet";
import { LabelsManager } from "../components/catalog/LabelsManager";
import { FiltersToggle } from "../components/FiltersToggle";
import { PageTools, ToolButton } from "../components/PageTools";
import { PickSheet } from "../components/PickSheet";
import { Table } from "../components/Table";
import { Editable, useViewOnly } from "../components/ViewOnly";
import { sortCategoryTree, useCategories, useLabels, useProducts } from "../hooks/useCatalog";
import { useDebouncedValue } from "../hooks/useDebouncedValue";
import { formatKopecks } from "../lib/money";
import { Icon } from "../components/Icon";

// Черновики — отдельным экраном («Черновики · N» в шапке), не фильтром списка.
const VISIBILITY_LABELS: Record<Exclude<ProductStatus, "draft">, string> = {
  active: "Активные",
  inactive: "Скрытые",
  deleted: "Удалённые",
};

const DRAFTS_QUERY = { search: "", status: "draft", label: "", category: null, stock: "", page: 1 } as const;

function visibilityBadge(product: ProductRow) {
  if (product.deleted_at) return <span className="badge badge-deleted">Удалён</span>;
  if (product.is_draft) return <span className="badge badge-warning">Черновик</span>;
  if (!product.is_active) return <span className="badge badge-blocked">Скрыт</span>;
  return <span className="badge badge-active">Активен</span>;
}

function errorText(error: unknown): string {
  if (!(error instanceof ApiError)) return "Действие не выполнено.";
  return Object.values(error.fieldErrors)[0]?.[0] ?? error.message;
}

export function ProductsPage() {
  const [search, setSearch] = useState("");
  const [visibility, setVisibility] = useState<ProductStatus | "">("");
  const [label, setLabel] = useState("");
  const [category, setCategory] = useState<number | null>(null);
  const [stock, setStock] = useState<StockFilter | "">("");
  const [moreFilters, setMoreFilters] = useState(false);
  const [page, setPage] = useState(1);
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [sheet, setSheet] = useState<"status" | "category" | "colors" | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const debouncedSearch = useDebouncedValue(search.trim());
  const viewOnly = useViewOnly();
  const categories = useCategories();
  const labels = useLabels();
  const query = { search: debouncedSearch, status: visibility, label, category, stock, page };
  const products = useProducts(query);
  const drafts = useProducts(DRAFTS_QUERY);
  const { data, loading, error } = products;

  // Другая страница или фильтр — выбор сбрасывается: действие касается только видимых строк.
  const queryKey = JSON.stringify(query);
  useEffect(() => setSelected(new Set()), [queryKey]);

  const pages = data ? Math.max(1, Math.ceil(data.count / PRODUCTS_PAGE_SIZE)) : 1;
  const resetPage = () => setPage(1);
  const rows = data?.results ?? [];
  const labelById = new Map((labels.data ?? []).map((item) => [item.id, item]));
  const allChecked = rows.length > 0 && rows.every((row) => selected.has(row.id));
  const leafCategories = batchCategories(categories.data ?? []);
  const showingDeleted = visibility === "deleted";

  function toggle(id: number) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  const checkedRows = rows.filter((row) => selected.has(row.id));

  async function apply(changes: Omit<ProductBulk, "ids">, done: string, ids = [...selected]) {
    setBusy(true);
    setActionError(null);
    setNotice(null);
    try {
      const result = await productsService.bulk({ ids, ...changes });
      setNotice(`${done}: ${result.updated}`);
      // Удалённые и восстановленные уходят из текущего списка — выбор с них снимается.
      if (changes.deleted !== undefined) setSelected(new Set());
      products.reload();
      labels.reload();
    } catch (err) {
      setActionError(errorText(err));
    } finally {
      setBusy(false);
    }
  }

  function removeProducts(ids: number[], name?: string) {
    const what = name ? `«${name}»` : `товары (${ids.length})`;
    if (!window.confirm(`Удалить ${what}? Пропадут с витрины, история заказов сохранится. Вернуть — фильтр «Удалённые».`)) return;
    void apply({ deleted: true }, "Удалено товаров", ids);
  }

  const labelValue = (value: string) => (value === "none" ? null : Number(value));

  return (
    <section>
      <div className="page-header">
        <h1>Товары</h1>
        {/* Одна кнопка: фото → один товар (обычная карточка) или сразу много (черновики). */}
        {viewOnly ? null : (
          <PageTools>
            <ToolButton icon="plus" label="Добавить товар" tone="accent" to="/catalog/products/batch" />
          </PageTools>
        )}
        {data ? <span className="muted page-sub">Всего: {data.count}</span> : null}
      </div>

      {drafts.data?.count ? (
        <Link to="/catalog/products/drafts" className="drafts-banner">
          <span className="badge badge-warning">Черновики · {drafts.data.count}</span>
          <span className="drafts-banner-text">Допишите цену и опубликуйте</span>
          <Icon name="right" size={18} />
        </Link>
      ) : null}

      <div className={moreFilters ? "filters is-open" : "filters"}>
        <input
          type="search"
          placeholder="Название или артикул"
          value={search}
          onChange={(event) => {
            setSearch(event.target.value);
            resetPage();
          }}
        />
        <select
          value={category ?? ""}
          aria-label="Категория"
          onChange={(event) => {
            setCategory(event.target.value ? Number(event.target.value) : null);
            resetPage();
          }}
        >
          <option value="">Все категории</option>
          {sortCategoryTree(categories.data ?? []).map((item) => (
            <option key={item.id} value={item.id}>
              {item.depth ? `— ${item.name}` : item.name}
            </option>
          ))}
        </select>
        <FiltersToggle
          open={moreFilters}
          active={[label, visibility, stock].filter(Boolean).length}
          onToggle={() => setMoreFilters((value) => !value)}
        />
        <select
          className="filters-extra"
          value={label}
          aria-label="Статус"
          onChange={(event) => {
            setLabel(event.target.value);
            resetPage();
          }}
        >
          <option value="">Любой статус</option>
          {(labels.data ?? []).map((item) => (
            <option key={item.id} value={item.id}>
              {item.name}
            </option>
          ))}
          <option value="none">Без статуса</option>
        </select>
        <select
          className="filters-extra"
          value={visibility}
          aria-label="Видимость"
          onChange={(event) => {
            setVisibility(event.target.value as ProductStatus | "");
            resetPage();
          }}
        >
          <option value="">Кроме удалённых</option>
          {Object.entries(VISIBILITY_LABELS).map(([value, text]) => (
            <option key={value} value={value}>
              {text}
            </option>
          ))}
        </select>
        <select
          className="filters-extra"
          value={stock}
          aria-label="Остаток"
          onChange={(event) => {
            setStock(event.target.value as StockFilter | "");
            resetPage();
          }}
        >
          <option value="">Любой остаток</option>
          <option value="in_stock">В наличии</option>
          <option value="out_of_stock">Нет в наличии</option>
        </select>
      </div>

      {error ? <p className="alert">{error}</p> : null}
      {actionError ? <p className="alert">{actionError}</p> : null}
      {notice ? <p className="note note-success">{notice}</p> : null}

      <Table loading={loading} className="table-products">
        <thead>
          <tr>
            <th className="check-cell">
              <input
                type="checkbox"
                aria-label="Отметить все на странице"
                disabled={viewOnly}
                checked={allChecked}
                onChange={() => setSelected(allChecked ? new Set() : new Set(rows.map((row) => row.id)))}
              />
            </th>
            <th className="thumb-cell" aria-label="Фото" />
            <th>Название</th>
            <th>Цена</th>
            <th>Остаток</th>
            <th>Статус</th>
            <th>Видимость</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((product) => {
            const current = product.status === null ? null : labelById.get(product.status);
            return (
              <tr key={product.id} className={selected.has(product.id) ? "is-selected" : undefined}>
                <td className="check-cell">
                  <label className="check-hit">
                    <input
                      type="checkbox"
                      aria-label={`Отметить ${product.name}`}
                      disabled={viewOnly}
                      checked={selected.has(product.id)}
                      onChange={() => toggle(product.id)}
                    />
                  </label>
                </td>
                <td className="thumb-cell">
                  {product.cover_url ? (
                    <img className="thumb" src={product.cover_url} alt="" />
                  ) : (
                    <div className="thumb thumb-empty" />
                  )}
                </td>
                <td>
                  <Link to={`/catalog/products/${product.id}`}>{product.name}</Link>
                  <div className="muted small">{product.category_name}</div>
                </td>
                <td>
                  {product.price_kopecks === null ? "По запросу" : formatKopecks(product.price_kopecks)}
                  {product.compare_at_kopecks ? (
                    <s className="muted old-price">{formatKopecks(product.compare_at_kopecks)}</s>
                  ) : null}
                </td>
                <td>{product.total_stock}</td>
                <td>
                  {/* Статус меняется прямо в списке — у одного товара. */}
                  <select
                    className={`label-select label-${current?.tone ?? "none"}`}
                    value={product.status ?? "none"}
                    disabled={busy || viewOnly || Boolean(product.deleted_at)}
                    aria-label={`Статус: ${product.name}`}
                    onChange={(e) =>
                      void apply({ status: labelValue(e.target.value) }, "Статус изменён у товаров", [product.id])
                    }
                  >
                    <option value="none">Без статуса</option>
                    {(labels.data ?? []).map((item) => (
                      <option key={item.id} value={item.id}>
                        {item.name}
                      </option>
                    ))}
                  </select>
                </td>
                <td>
                  <span className="row-tools">
                    {visibilityBadge(product)}
                    {product.deleted_at ? (
                      <button
                        type="button"
                        className="row-tool"
                        disabled={busy || viewOnly}
                        aria-label={`Восстановить ${product.name}`}
                        title="Восстановить"
                        onClick={() => void apply({ deleted: false }, "Восстановлено товаров", [product.id])}
                      >
                        <Icon name="undo" size={18} />
                      </button>
                    ) : (
                      <button
                        type="button"
                        className="row-tool row-tool-danger"
                        disabled={busy || viewOnly}
                        aria-label={`Удалить ${product.name}`}
                        title="Удалить"
                        onClick={() => removeProducts([product.id], product.name)}
                      >
                        <Icon name="trash" size={18} />
                      </button>
                    )}
                  </span>
                </td>
              </tr>
            );
          })}
          {data && rows.length === 0 ? (
            <tr>
              <td colSpan={7} className="empty">
                Ничего не найдено
              </td>
            </tr>
          ) : null}
        </tbody>
      </Table>

      <div className="pagination">
        <button
          type="button"
          className="button button-ghost"
          disabled={page <= 1 || loading}
          onClick={() => setPage((p) => p - 1)}
        >
          ← Назад
        </button>
        <span className="muted">
          Страница {page} из {pages}
        </span>
        <button
          type="button"
          className="button button-ghost"
          disabled={!data?.next || loading}
          onClick={() => setPage((p) => p + 1)}
        >
          Вперёд →
        </button>
      </div>

      {selected.size > 0 ? (
        <div className="batch-dock batch-actions bulk-dock" role="region" aria-label="Действия с отмеченными товарами">
          <div className="bulk-dock-head">
            <strong>Выбрано: {selected.size}</strong>
            {allChecked ? null : (
              <button type="button" className="bulk-link" onClick={() => setSelected(new Set(rows.map((row) => row.id)))}>
                <Icon name="check" size={14} />
                Все на странице
              </button>
            )}
            <button type="button" className="bulk-close" aria-label="Снять выбор" onClick={() => setSelected(new Set())}>
              <Icon name="close" size={18} />
            </button>
          </div>
          {showingDeleted ? (
            <div className="batch-actions-grid batch-actions-grid-1">
              <button
                type="button"
                className="batch-action is-primary"
                disabled={busy}
                onClick={() => void apply({ deleted: false }, "Восстановлено товаров")}
              >
                <Icon name="undo" />
                Восстановить
              </button>
            </div>
          ) : (
            <div className="batch-actions-grid batch-actions-grid-6">
              <button type="button" className="batch-action" disabled={busy || checkedRows.length < 2} onClick={() => setSheet("colors")}>
                <Icon name="palette" />
                Цвета
              </button>
              <button type="button" className="batch-action" disabled={busy} onClick={() => setSheet("status")}>
                <Icon name="tag" />
                Статус
              </button>
              <button type="button" className="batch-action" disabled={busy} onClick={() => setSheet("category")}>
                <Icon name="folder" />
                Категория
              </button>
              <button
                type="button"
                className="batch-action"
                disabled={busy}
                onClick={() => void apply({ is_active: false }, "Скрыто товаров")}
              >
                <Icon name="eyeOff" />
                Скрыть
              </button>
              <button
                type="button"
                className="batch-action"
                disabled={busy}
                onClick={() => void apply({ is_active: true }, "Показано товаров")}
              >
                <Icon name="eye" />
                Показать
              </button>
              <button
                type="button"
                className="batch-action is-danger"
                disabled={busy}
                onClick={() => removeProducts([...selected])}
              >
                <Icon name="trash" />
                Удалить
              </button>
            </div>
          )}
        </div>
      ) : null}

      {sheet === "colors" ? (
        <ColorLinkSheet
          rows={checkedRows}
          onDone={(updated) => {
            setSheet(null);
            setNotice(`Связано цветов: ${updated}`);
            products.reload();
          }}
          onClose={() => setSheet(null)}
        />
      ) : null}
      {sheet === "status" ? (
        <PickSheet
          title={`Статус · товаров: ${selected.size}`}
          options={[
            ...(labels.data ?? []).map((item) => ({ value: String(item.id), label: item.name, tone: item.tone })),
            { value: "none", label: "Без статуса" },
          ]}
          onPick={(value) => {
            setSheet(null);
            void apply({ status: labelValue(value) }, "Статус изменён у товаров");
          }}
          onClose={() => setSheet(null)}
        />
      ) : null}
      {sheet === "category" && categories.data ? (
        <CategorySheet
          title={`Категория · товаров: ${selected.size}`}
          categories={leafCategories}
          all={categories.data}
          counts={new Map(leafCategories.map((item) => [item.id, item.products_count]))}
          onPick={(item) => {
            setSheet(null);
            void apply({ category: item.id }, "Перенесено товаров");
          }}
          onClose={() => setSheet(null)}
        />
      ) : null}

      {labels.data ? (
        <Editable>
          <LabelsManager labels={labels.data} onChanged={labels.reload} />
        </Editable>
      ) : null}
    </section>
  );
}
