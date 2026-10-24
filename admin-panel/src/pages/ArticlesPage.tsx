import { useState } from "react";
import { Link } from "react-router";

import { ARTICLES_PAGE_SIZE, type ArticleRow, type ArticleStatus } from "../api/content";
import { useDebouncedValue } from "../hooks/useDebouncedValue";
import { useArticles } from "../hooks/useContent";
import { Table } from "../components/Table";

const STATUS_LABELS: Record<ArticleStatus, string> = {
  published: "Опубликованные",
  draft: "Черновики",
  deleted: "Удалённые",
};

function statusBadge(article: ArticleRow) {
  if (article.deleted_at) return <span className="badge badge-deleted">Удалена</span>;
  if (!article.is_published) return <span className="badge badge-blocked">Черновик</span>;
  return <span className="badge badge-active">Опубликована</span>;
}

function formatDate(value: string | null): string {
  return value ? new Date(value).toLocaleDateString("ru-RU") : "—";
}

export function ArticlesPage() {
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState<ArticleStatus | "">("");
  const [page, setPage] = useState(1);
  const debouncedSearch = useDebouncedValue(search.trim());
  const { data, loading, error } = useArticles({ search: debouncedSearch, status, page });
  const pages = data ? Math.max(1, Math.ceil(data.count / ARTICLES_PAGE_SIZE)) : 1;

  return (
    <section>
      <div className="page-header">
        <h1>Статьи</h1>
        {data ? <span className="muted">Всего: {data.count}</span> : null}
        <Link to="/content/articles/new" className="button header-action">
          Написать статью
        </Link>
      </div>
      <p className="muted">
        Статьи видны покупателям на вкладке «Контакты» на сайте и в приложении. Ссылки на мессенджеры
        задаются в настройках сервера (.env).
      </p>

      <div className="filters">
        <input
          type="search"
          placeholder="Заголовок"
          value={search}
          onChange={(event) => {
            setSearch(event.target.value);
            setPage(1);
          }}
        />
        <select
          value={status}
          onChange={(event) => {
            setStatus(event.target.value as ArticleStatus | "");
            setPage(1);
          }}
        >
          <option value="">Кроме удалённых</option>
          {Object.entries(STATUS_LABELS).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
      </div>

      {error ? <p className="alert">{error}</p> : null}

      <Table loading={loading}>
        <thead>
          <tr>
            <th aria-label="Обложка" />
            <th>Заголовок</th>
            <th>Фото</th>
            <th>Опубликована</th>
            <th>Статус</th>
          </tr>
        </thead>
        <tbody>
          {data?.results.map((article) => (
            <tr key={article.id}>
              <td>
                {article.cover_url ? (
                  <img className="thumb" src={article.cover_url} alt="" />
                ) : (
                  <div className="thumb thumb-empty" />
                )}
              </td>
              <td>
                <Link to={`/content/articles/${article.id}`}>{article.title}</Link>
                {article.excerpt ? <div className="muted small">{article.excerpt}</div> : null}
              </td>
              <td>{article.images_count}</td>
              <td className="muted">{formatDate(article.published_at)}</td>
              <td>{statusBadge(article)}</td>
            </tr>
          ))}
          {data && data.results.length === 0 ? (
            <tr>
              <td colSpan={5} className="empty">
                Статей пока нет
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
