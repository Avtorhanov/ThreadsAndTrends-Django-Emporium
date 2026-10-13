import type { AdminPayment, PaymentStatus, RefundStatus } from "../../api/orders";
import { formatKopecks } from "../../lib/money";

const dateFormat = new Intl.DateTimeFormat("ru-RU", { dateStyle: "short", timeStyle: "short" });

const PAYMENT_TONE: Record<PaymentStatus, string> = {
  pending: "warn",
  succeeded: "active",
  canceled: "deleted",
  refunded: "progress",
};

const REFUND_TONE: Record<RefundStatus, string> = {
  pending: "warn",
  succeeded: "active",
  canceled: "blocked",
};

type Props = {
  payments: AdminPayment[];
  canRetryRefund: boolean;
  busy: boolean;
  onRetryRefund: () => void;
  onSync: () => void;
};

/** Онлайн-оплата заказа: попытки, возвраты и ручные действия (сверка, повтор возврата).
 * Статусы платежей меняет только сверка с провайдером — вручную их не выставить. */
export function PaymentsCard({ payments, canRetryRefund, busy, onRetryRefund, onSync }: Props) {
  const hasPending = payments.some((payment) => payment.status === "pending");

  return (
    <div className="card">
      <h2>Оплата</h2>
      {payments.length === 0 ? <p className="muted">Покупатель ещё не переходил к оплате.</p> : null}
      <ul className="history">
        {payments.map((payment) => (
          <li key={payment.id}>
            <span>
              <span className={`badge badge-${PAYMENT_TONE[payment.status]}`}>
                {payment.status_display}
              </span>{" "}
              <strong>{formatKopecks(payment.amount_kopecks)}</strong>
            </span>
            <span className="muted small">
              {dateFormat.format(new Date(payment.created_at))}
              {payment.paid_at ? `, оплачен ${dateFormat.format(new Date(payment.paid_at))}` : ""}
              {payment.provider_payment_id ? ` · ЮKassa ${payment.provider_payment_id}` : ""}
              {payment.cancellation_reason ? ` · причина: ${payment.cancellation_reason}` : ""}
            </span>
            {payment.refunds.map((refund) => (
              <span key={refund.id} className="small">
                Возврат {formatKopecks(refund.amount_kopecks)} ({refund.reason_display}):{" "}
                <span className={`badge badge-${REFUND_TONE[refund.status]}`}>
                  {refund.status_display}
                </span>
                {refund.cancellation_reason ? (
                  <span className="muted"> · {refund.cancellation_reason}</span>
                ) : null}
              </span>
            ))}
          </li>
        ))}
      </ul>
      {hasPending || canRetryRefund ? (
        <div className="transitions">
          {hasPending ? (
            <button type="button" className="button button-ghost" disabled={busy} onClick={onSync}>
              Проверить оплату
            </button>
          ) : null}
          {canRetryRefund ? (
            <button type="button" className="button" disabled={busy} onClick={onRetryRefund}>
              Повторить возврат
            </button>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
