import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import "./tokens.css";
import "./fonts.css";
import "./styles.css";

async function start() {
  const root = document.getElementById("root");
  if (!root) throw new Error("Нет элемента #root");
  // Превью на GitHub Pages: ответы API из снимка. Подменить fetch нужно до создания клиента
  // API, поэтому App загружается после. В боевую сборку модуль превью не попадает.
  if (import.meta.env.VITE_PREVIEW === "1") {
    const { installPreview } = await import("./preview/mock");
    await installPreview();
  }
  const { App } = await import("./App");
  createRoot(root).render(
    <StrictMode>
      <App />
    </StrictMode>,
  );
}

void start();
