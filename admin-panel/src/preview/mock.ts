/**
 * Превью панели на GitHub Pages (сборка с VITE_PREVIEW=1): сервера нет, ответы admin-API
 * записаны заранее (deploy/preview/build.py → preview-api.json) на демо-данных.
 * Чтение — из снимка; изменения не сохраняются: сервер «соглашается» и возвращает данные
 * объекта как были. В боевую сборку модуль не попадает (динамический импорт под флагом).
 *
 * Вход имитируется: логин и пароль администратора превью лежат в снимке (`_login`) и
 * сверяются здесь, в браузере, — это не защита, на Pages только демо-данные. «Сессия» —
 * флаг в localStorage; его же ставит вход на странице «Вход» витрины превью
 * (deploy/preview/assets/preview.js), поэтому администратор попадает в панель оттуда.
 */

type Snapshot = Record<string, unknown>;

const API = "/api/v1/admin";
const SESSION = "didi-preview-admin";

type Login = { email: string; password: string };

/** Ключ снимка — как api_key() в deploy/preview/build.py. */
function snapshotKey(url: URL): string {
  const pairs = [...url.searchParams.entries()]
    .filter(([key, value]) => value !== "" && !(key === "page" && value === "1"))
    .sort(([a, av], [b, bv]) => (a === b ? av.localeCompare(bv) : a.localeCompare(b)));
  const query = pairs.map(([key, value]) => `${key}=${value}`).join("&");
  return url.pathname + (query ? `?${query}` : "");
}

function json(body: unknown, status = 200): Response {
  return new Response(status === 204 ? null : JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function signedIn(): boolean {
  try {
    return window.localStorage.getItem(SESSION) === "1";
  } catch {
    return false;
  }
}

function setSignedIn(value: boolean) {
  try {
    if (value) window.localStorage.setItem(SESSION, "1");
    else window.localStorage.removeItem(SESSION);
  } catch {
    // без хранилища вход не запомнится — после перезагрузки снова страница входа
  }
}

function banner() {
  const note = document.createElement("div");
  note.className = "preview-note";
  note.setAttribute("role", "note");
  note.textContent = "Превью: изменения не сохраняются";
  document.body.append(note);
}

export async function installPreview(): Promise<void> {
  const base = import.meta.env.BASE_URL;
  const response = await fetch(`${base}preview-api.json`);
  const snapshot = (await response.json()) as Snapshot;
  const realFetch = window.fetch.bind(window);

  const login = snapshot._login as Login;

  function read(url: URL): Response {
    const exact = snapshot[snapshotKey(url)];
    if (exact !== undefined) return json(exact);
    const byPath = snapshot[url.pathname];
    if (byPath !== undefined) return json(byPath);
    return json({ detail: "В превью нет этих данных." }, 404);
  }

  async function write(url: URL, request: Request): Promise<Response> {
    const path = url.pathname;
    if (path === `${API}/auth/login/`) {
      const body = (await request.clone().json()) as Partial<Login>;
      const ok =
        body.email?.trim().toLowerCase() === login.email && body.password === login.password;
      if (!ok) return json({ detail: "Неверный email или пароль." }, 400);
      setSignedIn(true);
      return json(snapshot[`${API}/auth/me/`]);
    }
    if (path === `${API}/auth/logout/`) {
      setSignedIn(false);
      return json(null, 204);
    }
    if (request.method === "DELETE") return json(null, 204);
    // Действие над объектом (…/{id}/transition/, …/restore/) → объект как был.
    const owner = path.replace(/[a-z-]+\/$/, "");
    const current = snapshot[path] ?? snapshot[owner];
    if (current !== undefined && !Array.isArray(current)) return json(current);
    let body: unknown = {};
    try {
      body = await request.clone().json();
    } catch {
      // загрузка файла (multipart) — тела-JSON нет
    }
    return json({ id: 0, ...(body as object) }, 201);
  }

  window.fetch = async (input: RequestInfo | URL, init?: RequestInit) => {
    const request = input instanceof Request ? input : new Request(input, init);
    const url = new URL(request.url, window.location.href);
    if (!url.pathname.startsWith("/api/")) return realFetch(input, init);
    if (url.pathname === `${API}/auth/csrf/`) return json(null, 204);
    if (url.pathname === `${API}/auth/me/` && !signedIn()) {
      return json({ detail: "Нужен вход." }, 401);
    }
    if (request.method === "GET") return read(url);
    return write(url, request);
  };

  banner();
}
