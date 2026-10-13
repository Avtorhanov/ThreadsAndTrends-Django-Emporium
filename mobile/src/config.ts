// Адрес бэкенда. Для эмулятора Android — http://10.0.2.2:8000, для устройства — IP компьютера в сети.
export const API_URL = (process.env.EXPO_PUBLIC_API_URL ?? "http://localhost:8000").replace(
  /\/+$/,
  "",
);
