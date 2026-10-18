// Веб-версия: Keychain/Keystore нет, refresh-токен — в localStorage этого домена.
// От кражи через XSS защищает Content-Security-Policy (только свои скрипты, deploy/Caddyfile);
// access-токен по-прежнему только в памяти, refresh одноразовый (ротация + чёрный список).
const REFRESH_KEY = "didi.refresh_token";

function storage(): Storage | null {
  try {
    return window.localStorage;
  } catch {
    return null; // приватный режим с запретом хранилища — вход живёт до закрытия вкладки
  }
}

let memory: string | null = null;

export const tokenStorage = {
  async getRefresh(): Promise<string | null> {
    return storage()?.getItem(REFRESH_KEY) ?? memory;
  },
  async setRefresh(token: string): Promise<void> {
    memory = token;
    storage()?.setItem(REFRESH_KEY, token);
  },
  async clear(): Promise<void> {
    memory = null;
    storage()?.removeItem(REFRESH_KEY);
  },
};
