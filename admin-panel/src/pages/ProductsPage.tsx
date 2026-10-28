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
import { LabelsManager } from "../components/catalog/LabelsManager";
import { Table } from "../components/Table";
import { isLeaf, sortCategoryTree, useCategories, useLabels, useProducts } from "../hooks/useCatalog";
import { useDebouncedValue } from "../hooks/useDebouncedValue";
import { formatKopecks } from "../lib/money";

const VISIBILITY_LABELS: Record<ProductStatus, string> = {
  active: "Активные",
  inactive: "Скрытые",
  deleted: "Удалённые",
};

function visibilityBadge(product: ProductRow) {
  if (product.deleted_at) return <span className="badge badge-deleted">Удалён</span>;
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
  const [page, setPage] = useState(1);
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [bulkLabel, setBulkLabel] = useState("");
  const [bulkCategory, setBulkCategory] = useState("");
  const [notice, setNotice] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const debouncedSearch = useDebouncedValue(search.trim());
  const categories = useCategories();
  const labels = useLabels();
  const query = { search: debouncedSearch, status: visibility, label, category, stock, page };
  const products = useProducts(query);
  const { data, loading, error } = products;

  // Другая страница или фильтр — выбор сбрасывается: действие касается только видимых строк.
  const queryKey = JSON.stringify(query);
  useEffect(() => setSelected(new Set()), [queryKey]);

  const pages = data ? Math.max(1, Math.ceil(data.count / PRODUCTS_PAGE_SIZE)) : 1;
  const resetPage = () => setPage(1);
  const rows = data?.results ?? [];
  const labelById = new Map((labels.data ?? []).map((item) => [item.id, item]));
  const allChecked = rows.length > 0 && rows.every((row) => selected.has(row.id));
  const leafCategories = sortCategoryTree(categories.data ?? []).filter(isLeaf);

  function toggle(id: number) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  async function apply(changes: Omit<ProductBulk, "ids">, done: string, ids = [...selected]) {
    setBusy(true);
    setActionError(null);
    setNotice(null);
    try {
      const result = await productsService.bulk({ ids, ...changes });
      setNotice(`${done}: ${result.updated}`);
      products.reload();
      labels.reload();
    } catch (err) {
      setActionError(errorText(err));
    } finally {
      setBusy(false);
    }
  }

  const labelValue = (value: string) => (value === "none" ? null : Number(value));

  return (
    <section>
      <div className="page-header">
        <h1>Товары</h1>
        {data ? <span className="muted">Всего: {data.count}</span> : null}
        <Link to="/catalog/products/new" className="button header-action">
          Добавить товар
        </Link>
      </div>

      <div className="filters">
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
        <select
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

      {selected.size > 0 ? (
        <div className="bulk-bar" role="region" aria-label="Действия с отмеченными товарами">
          <strong>Выбрано: {selected.size}</strong>
          <button type="button" className="bulk-link" onClick={() => setSelected(new Set())}>
            Снять выбор
          </button>
          <span className="bulk-gap" />
          <label className="bulk-field">
            Статус
            <select value={bulkLabel} onChange={(e) => setBulkLabel(e.target.value)}>
              <option value="">Выберите…</option>
              {(labels.data ?? []).map((item) => (
                <option key={item.id} value={item.id}>
                  {item.name}
                </option>
              ))}
              <option value="none">Без статуса</option>
            </select>
          </label>
          <button
            type="button"
            className="button button-accent"
            disabled={busy || !bulkLabel}
            onClick={() => void apply({ status: labelValue(bulkLabel) }, "Статус изменён у товаров")}
          >
            Сменить статус
          </button>
          <label className="bulk-field">
            Категория
            <select value={bulkCategory} onChange={(e) => setBulkCategory(e.target.value)}>
              <option value="">Выберите…</option>
              {leafCategories.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.depth ? `— ${item.name}` : item.name}
                </option>
              ))}
            </select>
          </label>
          <button
            type="button"
            className="button button-outline"
            disabled={busy || !bulkCategory}
            onClick={() => void apply({ category: Number(bulkCategory) }, "Перенесено товаров")}
          >
            Перенести
          </button>
          <button
            type="button"
            className="button button-outline"
            disabled={busy}
            onClick={() => void apply({ is_active: false }, "Скрыто товаров")}
          >
            Скрыть
          </button>
          <button
            type="button"
            className="button button-outline"
            disabled={busy}
            onClick={() => void apply({ is_active: true }, "Показано товаров")}
          >
            Показать
          </button>
        </div>
      ) : null}

      <Table loading={loading}>
        <thead>
          <tr>
            <th className="check-cell">
              <input
                type="checkbox"
                aria-label="Отметить все на странице"
                checked={allChecked}
                onChange={() => setSelected(allChecked ? new Set() : new Set(rows.map((row) => row.id)))}
              />
            </th>
            <th aria-label="Фото" />
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
                  <input
                    type="checkbox"
                    aria-label={`Отметить ${product.name}`}
                    checked={selected.has(product.id)}
                    onChange={() => toggle(product.id)}
                  />
                </td>
                <td>
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
                    disabled={busy || Boolean(product.deleted_at)}
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
                <td>{visibilityBadge(product)}</td>
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

      {labels.data ? <LabelsManager labels={labels.data} onChanged={labels.reload} /> : null}
    </section>
  );
}
