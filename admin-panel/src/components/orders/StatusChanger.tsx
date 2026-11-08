import { useState } from "react";

import type { AdminOrderDetail, OrderStatus } from "../../api/orders";
import { agreementChannel } from "../../lib/agreement";
import { MARK_LABELS, isAwaitingAgreement, orderSteps, stepIndex } from "../../lib/orderFlow";

const COMMENT_MAX = 500;

const PLACEHOLDERS: Partial<Record<OrderStatus, string>> = {
  confirmed: "Например: оплата переводом, доставка в четверг",
  assembled: "Например: собрали, передадим курьеру завтра до 12:00",
  shipped: "Например: курьер позвонит за час",
  ready_for_pickup: "Например: заказ ждёт вас 7 дней, возьмите паспорт",
  delivered: "Например: спасибо за покупку!",
  cancelled: "Причина отмены — покупатель увидит её в письме и истории",
};

const dateFormat = new Intl.DateTimeFormat("ru-RU", { dateStyle: "short", timeStyle: "short" });

type Props = {
  order: AdminOrderDetail;
  busy: boolean;
  onSubmit: (status: OrderStatus, comment: string, notify: boolean) => Promise<boolean>;
};

/**
 * Обработка заказа: полоса шагов (Принят · Собран · В пути / В пункте выдачи · Получен),
 * уведомление покупателю с комментарием и предпросмотром, «Отметить: …» и отмена.
 * Отмена необратима — сначала показывает предупреждение и просит подтвердить.
 */
export function StatusChanger({ order, busy, onSubmit }: Props) {
  const [comment, setComment] = useState("");
  const [notify, setNotify] = useState(true);
  const [cancelling, setCancelling] = useState(false);
  const canNotify = order.customer !== null && !order.customer.is_deleted;
  const sendMail = notify && canNotify;
  const steps = orderSteps(order.delivery_method);
  const pending = isAwaitingAgreement(order.status);
  const reached = stepIndex(order.status);
  const channel = agreementChannel(order.agreement_channel);
  const forward = order.allowed_transitions.filter((item) => item.status !== "cancelled");
  const cancel = order.allowed_transitions.find((item) => item.status === "cancelled");
  const target = cancelling ? cancel : forward[0];
  const last = order.status_history[order.status_history.length - 1];
  const text = comment.trim().replace(/\s+/g, " ");

  async function submit(status: OrderStatus) {
    if (await onSubmit(status, text, sendMail)) {
      setComment("");
      setCancelling(false);
    }
  }

  return (
    <div className="card status-card">
      <div className="status-head">
        <h2>Статус заказа</h2>
        {last ? (
          <span className="muted small">
            {last.notified ? "Покупателю ушло письмо" : "Без письма покупателю"} ·{" "}
            {dateFormat.format(new Date(last.created_at))}
          </span>
        ) : null}
      </div>

      <ol className={reached < 0 ? "status-track is-cancelled" : "status-track"} aria-label="Обработка заказа">
        {steps.map((label, index) => {
          const done = !pending && index <= reached;
          const current = !pending && index === reached;
          return (
            <li
              key={label}
              className={done ? (current ? "is-done is-current" : "is-done") : undefined}
              aria-current={current ? "step" : undefined}
            >
              {label}
            </li>
          );
        })}
      </ol>
      {reached < 0 ? <p className="note note-info">Заказ отменён.</p> : null}
      {pending ? (
        <p className="note note-warning">
          Ждёт согласования: покупатель напишет вам{channel ? ` в ${channel.label}` : ""} с номером{" "}
          <b>{order.number}</b>. Договоритесь об оплате и доставке и отметьте «Принят» — иначе заказ отменится
          автоматически. Товар уже отложен.
        </p>
      ) : null}
      {order.status === "awaiting_payment" ? (
        <p className="muted small">Ждём оплату — после неё заказ можно собирать.</p>
      ) : null}
      {last?.comment ? <p className="status-last-comment">«{last.comment}»</p> : null}

      {order.allowed_transitions.length === 0 ? (
        reached === 3 ? <p className="muted">Заказ получен — статус окончательный.</p> : null
      ) : (
        <>
          <div className="status-box">
            <span className="status-box-title">Покупатель получит уведомление</span>
            <label className={sendMail ? "notify-chip is-on" : "notify-chip"}>
              <input
                type="checkbox"
                checked={sendMail}
                disabled={!canNotify || busy}
                onChange={(event) => setNotify(event.target.checked)}
              />
              {order.customer === null
                ? "Гость — email нет, письмо не отправить"
                : canNotify
                  ? `Письмо на ${order.customer.email}`
                  : "Аккаунт удалён — письмо не отправить"}
            </label>

            <label className="field">
              <span>Комментарий для покупателя — необязательно</span>
              <textarea
                rows={2}
                maxLength={COMMENT_MAX}
                value={comment}
                placeholder={(target && PLACEHOLDERS[target.status]) ?? "Пояснение к новому статусу"}
                onChange={(event) => setComment(event.target.value)}
              />
              <span className="muted small">
                {comment.length} / {COMMENT_MAX} · виден в истории заказа на сайте и в приложении
              </span>
            </label>

            {sendMail && target ? (
              <div className="notice-preview" aria-label="Предпросмотр письма">
                <span className="notice-logo" aria-hidden="true">
                  DiDi
                </span>
                <div>
                  <div className="notice-top">
                    <strong>
                      DiDi-shop: заказ {order.number} — {target.label.toLowerCase()}
                    </strong>
                    <span className="muted small">сейчас</span>
                  </div>
                  <p>
                    Статус заказа {order.number} изменился: {target.label}.
                    {text ? ` Комментарий магазина: ${text}` : ""}
                  </p>
                </div>
              </div>
            ) : null}
          </div>

          {cancelling ? (
            <p className="note note-info">
              Остатки вернутся на склад; оплаченный заказ уйдёт на возврат денег. Отмену не отменить.
            </p>
          ) : null}

          <div className="status-actions">
            {cancel && cancelling ? (
              <>
                <button type="button" className="button button-ghost" disabled={busy} onClick={() => setCancelling(false)}>
                  Не отменять
                </button>
                <button
                  type="button"
                  className="button button-danger-solid status-main"
                  disabled={busy}
                  onClick={() => void submit("cancelled")}
                >
                  Подтвердить отмену
                </button>
              </>
            ) : (
              <>
                {cancel ? (
                  <button type="button" className="button button-danger" disabled={busy} onClick={() => setCancelling(true)}>
                    Отменить заказ
                  </button>
                ) : null}
                {forward.map((item) => (
                  <button
                    key={item.status}
                    type="button"
                    className="button status-main"
                    disabled={busy}
                    onClick={() => void submit(item.status)}
                  >
                    Отметить: {MARK_LABELS[item.status] ?? item.label.toLowerCase()}
                  </button>
                ))}
              </>
            )}
          </div>
        </>
      )}
    </div>
  );
}
