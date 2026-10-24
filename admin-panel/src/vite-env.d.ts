/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** "1" — сборка для превью на GitHub Pages (ответы API из снимка, src/preview/mock.ts). */
  readonly VITE_PREVIEW?: string;
}
