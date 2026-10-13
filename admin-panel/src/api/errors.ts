export type FieldErrors = Record<string, string[]>;

/** Ошибка API: общее сообщение + ошибки по полям (формат DRF). */
export class ApiError extends Error {
  readonly status: number;
  readonly fieldErrors: FieldErrors;

  constructor(status: number, message: string, fieldErrors: FieldErrors = {}) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.fieldErrors = fieldErrors;
  }
}

const STATUS_MESSAGES: Record<number, string> = {
  401: "Сессия истекла, войдите снова.",
  403: "Недостаточно прав или устарел CSRF-токен. Обновите страницу.",
  404: "Не найдено.",
  429: "Слишком много попыток. Попробуйте позже.",
};

export function toApiError(status: number, body: unknown): ApiError {
  if (body && typeof body === "object" && !Array.isArray(body)) {
    const record = body as Record<string, unknown>;
    if (typeof record.detail === "string") return new ApiError(status, record.detail);
    const fieldErrors: FieldErrors = {};
    for (const [key, value] of Object.entries(record)) {
      if (Array.isArray(value)) fieldErrors[key] = value.map(String);
      else if (typeof value === "string") fieldErrors[key] = [value];
    }
    if (Object.keys(fieldErrors).length > 0) {
      const general = fieldErrors.non_field_errors?.[0];
      return new ApiError(status, general ?? "Проверьте введённые данные.", fieldErrors);
    }
  }
  return new ApiError(status, STATUS_MESSAGES[status] ?? "Ошибка сервера. Попробуйте позже.");
}

export const NETWORK_ERROR = new ApiError(0, "Нет соединения с сервером.");
