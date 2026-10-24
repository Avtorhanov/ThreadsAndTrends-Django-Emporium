import { useState } from "react";
import { Link } from "react-router";

import { PRODUCTS_PAGE_SIZE, type ProductRow, type ProductStatus, type StockFilter } from "../api/catalog";
import { sortCategoryTree, useCategories, useProducts } from "../hooks/useCatalog";
import { useDebouncedValue } from "../hooks/useDebouncedValue";
import { formatKopecks } from "../lib/money";
import { Table } from "../components/Table";

const STATUS_LABELS: Record<ProductStatus, string> = {
  active: "Активные",
  inactive: "Скрытые",
  deleted: "Удалённые",
};

function statusBadge(product: ProductRow) {
  if (product.deleted_at) return <span className="badge badge-deleted">Удалён</span>;
  if (!product.is_active) return <span className="badge badge-blocked">Скрыт</span>;
  return <span className="badge badge-active">Активен</span>;
}

export function ProductsPage() {
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState<ProductStatus | "">("");
  const [category, setCategory] = useState<number | null>(null);
  const [stock, setStock] = useState<StockFilter | "">("");
  const [page, setPage] = useState(1);
  const debouncedSearch = useDebouncedValue(search.trim());
  const categories = useCategories();
  const { data, loading, error } = useProducts({
    search: debouncedSearch,
    status,
    category,
    stock,
    page,
  });

  const pages = data ? Math.max(1, Math.ceil(data.count / PRODUCTS_PAGE_SIZE)) : 1;
  const resetPage = () => setPage(1);

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
          value={status}
          onChange={(event) => {
            setStatus(event.target.value as ProductStatus | "");
            resetPage();
          }}
        >
          <option value="">Кроме удалённых</option>
          {Object.entries(STATUS_LABELS).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
        <select
          value={stock}
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

      <Table loading={loading}>
        <thead>
          <tr>
            <th aria-label="Фото" />
            <th>Название</th>
            <th>Категория</th>
            <th>Цена</th>
            <th>Остаток</th>
            <th>Статус</th>
          </tr>
        </thead>
        <tbody>
          {data?.results.map((product) => (
            <tr key={product.id}>
              <td>
                {product.cover_url ? (
                  <img className="thumb" src={product.cover_url} alt="" />
                ) : (
                  <div className="thumb thumb-empty" />
                )}
              </td>
              <td>
                <Link to={`/catalog/products/${product.id}`}>{product.name}</Link>
              </td>
              <td className="muted">{product.category_name}</td>
              <td>
                {formatKopecks(product.price_kopecks)}
                {product.compare_at_kopecks ? (
                  <s className="muted old-price">{formatKopecks(product.compare_at_kopecks)}</s>
                ) : null}
              </td>
              <td>{product.total_stock}</td>
              <td>{statusBadge(product)}</td>
            </tr>
          ))}
          {data && data.results.length === 0 ? (
            <tr>
              <td colSpan={6} className="empty">
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
    </section>
  );
}
