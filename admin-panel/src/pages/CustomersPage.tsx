import { useState } from "react";

import {
  type Customer,
  type CustomerStatus,
  customersService,
  PAGE_SIZE,
} from "../api/customers";
import { ApiError } from "../api/errors";
import { useCustomers } from "../hooks/useCustomers";
import { useDebouncedValue } from "../hooks/useDebouncedValue";

const STATUS_LABELS: Record<CustomerStatus, string> = {
  active: "Активен",
  blocked: "Заблокирован",
  deleted: "Удалён",
};

const dateFormat = new Intl.DateTimeFormat("ru-RU", { dateStyle: "short", timeStyle: "short" });

function formatDate(value: string | null | undefined): string {
  return value ? dateFormat.format(new Date(value)) : "—";
}

type Action = "block" | "unblock" | "remove";

const ACTION_CONFIRM: Record<Action, string | null> = {
  block: "Заблокировать клиента? Он будет разлогинен на всех устройствах.",
  unblock: null,
  remove: "Удалить клиента? Профиль будет обезличен, действие необратимо.",
};

export function CustomersPage() {
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState<CustomerStatus | "">("");
  const [page, setPage] = useState(1);
  const debouncedSearch = useDebouncedValue(search.trim());
  const { data, loading, error, replace } = useCustomers({
    search: debouncedSearch,
    status,
    page,
  });
  const [busyId, setBusyId] = useState<number | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const pages = data ? Math.max(1, Math.ceil(data.count / PAGE_SIZE)) : 1;

  async function run(action: Action, customer: Customer) {
    const question = ACTION_CONFIRM[action];
    if (question && !window.confirm(`${question}\n\n${customer.email}`)) return;
    setBusyId(customer.id);
    setActionError(null);
    try {
      replace(await customersService[action](customer.id));
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : "Действие не выполнено.");
    } finally {
      setBusyId(null);
    }
  }

  return (
    <section>
      <div className="page-header">
        <h1>Клиенты</h1>
        {data ? <span className="muted">Всего: {data.count}</span> : null}
      </div>

      <div className="filters">
        <input
          type="search"
          placeholder="Email, имя или фамилия"
          value={search}
          onChange={(event) => {
            setSearch(event.target.value);
            setPage(1);
          }}
        />
        <select
          value={status}
          onChange={(event) => {
            setStatus(event.target.value as CustomerStatus | "");
            setPage(1);
          }}
        >
          <option value="">Все статусы</option>
          {Object.entries(STATUS_LABELS).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
      </div>

      {error ? <p className="alert">{error}</p> : null}
      {actionError ? <p className="alert">{actionError}</p> : null}

      <div className="table-wrap">
        <table className={loading ? "table is-loading" : "table"}>
          <thead>
            <tr>
              <th>Email</th>
              <th>Имя</th>
              <th>Статус</th>
              <th>Регистрация</th>
              <th>Последний вход</th>
              <th aria-label="Действия" />
            </tr>
          </thead>
          <tbody>
            {data?.results.map((customer) => (
              <tr key={customer.id}>
                <td>{customer.email}</td>
                <td>{[customer.first_name, customer.last_name].filter(Boolean).join(" ") || "—"}</td>
                <td>
                  <span className={`badge badge-${customer.status}`}>
                    {STATUS_LABELS[customer.status]}
                  </span>
                </td>
                <td>{formatDate(customer.date_joined)}</td>
                <td>{formatDate(customer.last_login)}</td>
                <td className="actions">
                  {customer.status === "active" ? (
                    <button
                      type="button"
                      className="button button-ghost"
                      disabled={busyId === customer.id}
                      onClick={() => void run("block", customer)}
                    >
                      Заблокировать
                    </button>
                  ) : null}
                  {customer.status === "blocked" ? (
                    <button
                      type="button"
                      className="button button-ghost"
                      disabled={busyId === customer.id}
                      onClick={() => void run("unblock", customer)}
                    >
                      Разблокировать
                    </button>
                  ) : null}
                  {customer.status !== "deleted" ? (
                    <button
                      type="button"
                      className="button button-danger"
                      disabled={busyId === customer.id}
                      onClick={() => void run("remove", customer)}
                    >
                      Удалить
                    </button>
                  ) : null}
                </td>
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
        </table>
      </div>

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
