import createClient from "openapi-fetch";

import { session } from "../auth/session";
import { API_URL } from "../config";
import { NETWORK_ERROR, toApiError } from "./errors";
import type { paths } from "./schema";

/** fetch с access-токеном: на 401 один раз обновляет пару токенов и повторяет запрос. */
async function authFetch(request: Request): Promise<Response> {
  const retry = request.clone();
  const access = session.getAccess();
  if (access) request.headers.set("Authorization", `Bearer ${access}`);

  const response = await fetch(request);
  if (response.status !== 401 || !access) return response;

  const fresh = await session.refresh().catch(() => null);
  if (!fresh) return response;
  retry.headers.set("Authorization", `Bearer ${fresh}`);
  return fetch(retry);
}

export const api = createClient<paths>({ baseUrl: API_URL, fetch: authFetch });

type FetchResult<T> = { data?: T; error?: unknown; response: Response };

/** Данные успешного ответа или ApiError с сообщением и ошибками полей. */
export async function unwrap<T>(request: Promise<FetchResult<T>>): Promise<T> {
  let result: FetchResult<T>;
  try {
    result = await request;
  } catch {
    throw NETWORK_ERROR;
  }
  if (!result.response.ok) {
    throw toApiError(result.response.status, result.error);
  }
  return result.data as T;
}
