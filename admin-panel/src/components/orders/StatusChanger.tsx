import { useState } from "react";

import type { AdminOrderDetail, OrderStatus } from "../../api/orders";

const COMMENT_MAX = 500;

// Необратимые переходы: предупреждение прямо в форме, отдельный confirm не нужен.
const WARNINGS: Partial<Record<OrderStatus, string>> = {
  cancelled: "Остатки вернутся на склад; оплаченный заказ уйдёт на возврат денег.",
  delivered: "Статус станет окончательным.",
};

const PLACEHOLDERS: Partial<Record<OrderStatus, string>> = {
  assembled: "Например: собрали, передадим курьеру завтра до 12:00",
  shipped: "Например: курьер позвонит за час до приезда",
  ready_for_pickup: "Например: заказ ждёт вас 7 дней, возьмите паспорт",
  cancelled: "Причина отмены — клиент увидит её в письме и истории",
};

const dateFormat = new Intl.DateTimeFormat("ru-RU", { dateStyle: "short", timeStyle: "short" });

type Props = {
  order: AdminOrderDetail;
  busy: boolean;
  onSubmit: (status: OrderStatus, comment: string, notify: boolean) => Promise<boolean>;
};

/**
 * Смена статуса: выбор следующего шага → комментарий для клиента → предпросмотр письма.
 * Рядом с текущим статусом — что клиент узнал в последний раз.
 */
export function StatusChanger({ order, busy, onSubmit }: Props) {
  const [target, setTarget] = useState<OrderStatus | null>(null);
  const [comment, setComment] = useState("");
  const [notify, setNotify] = useState(true);
  const canNotify = !order.customer.is_deleted;
  const option = order.allowed_transitions.find((item) => item.status === target);
  const last = order.status_history[order.status_history.length - 1];
  const text = comment.trim().replace(/\s+/g, " ");

  function pick(status: OrderStatus) {
    setTarget(status === target ? null : status);
    setNotify(canNotify);
  }

  async function submit() {
    if (!target) return;
    if (await onSubmit(target, text, notify && canNotify)) {
      setTarget(null);
      setComment("");
    }
  }

  return (
    <div className="card status-card">
      <div className="status-head">
        <h2>Статус</h2>
        {last ? (
          <span className="muted small">
            {last.notified ? "Клиенту отправлено письмо" : "Клиент не уведомлялся письмом"} ·{" "}
            {dateFormat.format(new Date(last.created_at))}
          </span>
        ) : null}
      </div>
      {last?.comment ? <p className="status-last-comment">«{last.comment}»</p> : null}

      {order.allowed_transitions.length === 0 ? (
        <p className="muted">Статус окончательный.</p>
      ) : (
        <div className="transitions" role="group" aria-label="Следующий статус">
          {order.allowed_transitions.map((item) => {
            const danger = item.status === "cancelled";
            const active = item.status === target;
            const base = danger ? "button button-danger" : "button button-outline";
            return (
              <button
                key={item.status}
                type="button"
                className={active ? `${base} is-active` : base}
                aria-pressed={active}
                disabled={busy}
                onClick={() => pick(item.status)}
              >
                {danger ? "Отменить заказ" : `→ ${item.label}`}
              </button>
            );
          })}
        </div>
      )}

      {option ? (
        <div className="status-compose">
          <label className="field">
            <span>Комментарий для клиента — необязательно</span>
            <textarea
              rows={3}
              maxLength={COMMENT_MAX}
              value={comment}
              placeholder={PLACEHOLDERS[option.status] ?? "Пояснение к новому статусу"}
              onChange={(event) => setComment(event.target.value)}
            />
            <span className="muted small">
              {comment.length} / {COMMENT_MAX} · виден в истории заказа на сайте и в приложении
            </span>
          </label>

          <label className="check">
            <input
              type="checkbox"
              checked={notify && canNotify}
              disabled={!canNotify}
              onChange={(event) => setNotify(event.target.checked)}
            />
            {canNotify ? `Отправить письмо на ${order.customer.email}` : "Аккаунт клиента удалён — письмо не отправить"}
          </label>

          {notify && canNotify ? (
            <div className="mail-preview" aria-label="Предпросмотр письма">
              <span className="muted small">Клиент получит</span>
              <strong>
                DiDi-shop: заказ {order.number} — {option.label.toLowerCase()}
              </strong>
              <p>
                Статус заказа {order.number} изменился: {option.label}.
                {text ? (
                  <>
                    <br />
                    Комментарий магазина: {text}
                  </>
                ) : null}
              </p>
            </div>
          ) : null}

          {WARNINGS[option.status] ? <p className="note note-info">{WARNINGS[option.status]}</p> : null}

          <div className="status-actions">
            <button
              type="button"
              className={option.status === "cancelled" ? "button button-danger" : "button button-accent"}
              disabled={busy}
              onClick={() => void submit()}
            >
              {option.status === "cancelled" ? "Отменить заказ" : `Перевести в «${option.label}»`}
            </button>
            <button type="button" className="button button-ghost" disabled={busy} onClick={() => setTarget(null)}>
              Не менять
            </button>
          </div>
        </div>
      ) : null}
    </div>
  );
}
