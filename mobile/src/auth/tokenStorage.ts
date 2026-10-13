import * as SecureStore from "expo-secure-store";

// Refresh-токен — в Keychain/Keystore. Access живёт только в памяти (15 минут).
const REFRESH_KEY = "didi.refresh_token";

export const tokenStorage = {
  getRefresh: () => SecureStore.getItemAsync(REFRESH_KEY),
  setRefresh: (token: string) => SecureStore.setItemAsync(REFRESH_KEY, token),
  clear: () => SecureStore.deleteItemAsync(REFRESH_KEY),
};
