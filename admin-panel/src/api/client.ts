import createClient from "openapi-fetch";

import { NETWORK_ERROR, toApiError } from "./errors";
import type { paths } from "./schema";

const SAFE_METHODS = new Set(["GET", "HEAD", "OPTIONS"]);

function readCookie(name: string): string | null {
  const match = document.cookie.split("; ").find((part) => part.startsWith(`${name}=`));
  return match ? decodeURIComponent(match.slice(name.length + 1)) : null;
}

let unauthorizedHandler: (() => void) | null = null;

/** Вызывается при любом 401: сессия истекла или пользователь вышел в другой вкладке. */
export function onUnauthorized(handler: (() => void) | null) {
  unauthorizedHandler = handler;
}

// Тот же origin, что и API: cookie сессии уходит автоматически, CORS не нужен.
export const api = createClient<paths>({ baseUrl: "", credentials: "same-origin" });

api.use({
  onRequest({ request }) {
    if (!SAFE_METHODS.has(request.method)) {
      // Django ротирует CSRF-токен при входе, поэтому cookie читается на каждый запрос.
      const token = readCookie("csrftoken");
      if (token) request.headers.set("X-CSRFToken", token);
    }
    return request;
  },
  onResponse({ request, response }) {
    if (response.status === 401 && !request.url.endsWith("/api/v1/admin/auth/login/")) {
      unauthorizedHandler?.();
    }
    return response;
  },
});

type FetchResult<T> = { data?: T; error?: unknown; response: Response };

export async function unwrap<T>(request: Promise<FetchResult<T>>): Promise<T> {
  let result: FetchResult<T>;
  try {
    result = await request;
  } catch {
    throw NETWORK_ERROR;
  }
  if (!result.response.ok) throw toApiError(result.response.status, result.error);
  return result.data as T;
}
