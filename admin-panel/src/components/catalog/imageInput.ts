import { useEffect, useRef } from "react";

/** Форматы, которые принимает сервер (store.services.images), и предел размера файла. */
export const ACCEPTED_TYPES = ["image/jpeg", "image/png", "image/webp"] as const;
export const MAX_IMAGE_BYTES = 5 * 1024 * 1024;
const MAX_SIDE = 2560;

function accepted(type: string): boolean {
  return (ACCEPTED_TYPES as readonly string[]).includes(type);
}

function toBlob(canvas: HTMLCanvasElement, quality: number): Promise<Blob | null> {
  return new Promise((resolve) => canvas.toBlob(resolve, "image/jpeg", quality));
}

async function decode(blob: Blob): Promise<CanvasImageSource & { width: number; height: number }> {
  if ("createImageBitmap" in window) {
    try {
      return await createImageBitmap(blob);
    } catch {
      // Safari старых версий не декодирует часть форматов через createImageBitmap — ниже <img>.
    }
  }
  const url = URL.createObjectURL(blob);
  try {
    const image = new Image();
    image.src = url;
    await image.decode();
    return image;
  } finally {
    URL.revokeObjectURL(url);
  }
}

/**
 * Фото из буфера обмена и перетаскивания: подходящий файл — как есть; слишком большой или в
 * другом формате (PNG-копия снимка с телефона на 10+ МБ, HEIC, TIFF) — перекодируется в JPEG
 * со стороной до 2560 px. Не удалось — null (вызывающий скажет, что файл пропущен).
 */
export async function normalizeImage(blob: Blob, name: string): Promise<File | null> {
  if (accepted(blob.type) && blob.size <= MAX_IMAGE_BYTES) {
    return blob instanceof File ? blob : new File([blob], name, { type: blob.type });
  }
  if (!blob.type.startsWith("image/")) return null;
  try {
    const source = await decode(blob);
    const k = Math.min(1, MAX_SIDE / Math.max(source.width, source.height));
    const canvas = document.createElement("canvas");
    canvas.width = Math.max(1, Math.round(source.width * k));
    canvas.height = Math.max(1, Math.round(source.height * k));
    const context = canvas.getContext("2d");
    if (!context) return null;
    context.drawImage(source, 0, 0, canvas.width, canvas.height);
    for (const quality of [0.88, 0.75, 0.6]) {
      const jpeg = await toBlob(canvas, quality);
      if (jpeg && jpeg.size <= MAX_IMAGE_BYTES) {
        return new File([jpeg], name.replace(/\.[a-z0-9]+$/i, "") + ".jpg", { type: "image/jpeg" });
      }
    }
  } catch {
    return null;
  }
  return null;
}

let pasteCounter = 0;
function pastedName(type: string): string {
  pasteCounter += 1;
  const ext = type.split("/")[1]?.replace("jpeg", "jpg") ?? "png";
  return `Вставка-${pasteCounter}.${ext}`;
}

/** Картинки из события вставки (⌘/Ctrl+V) или перетаскивания. */
export function imagesFrom(data: DataTransfer | null): { blob: Blob; name: string }[] {
  if (!data) return [];
  const files = Array.from(data.files).filter((file) => file.type.startsWith("image/"));
  if (files.length) return files.map((file) => ({ blob: file, name: file.name || pastedName(file.type) }));
  // Скриншот из буфера бывает только в items, без files.
  return Array.from(data.items)
    .filter((item) => item.kind === "file" && item.type.startsWith("image/"))
    .map((item) => item.getAsFile())
    .filter((file): file is File => file !== null)
    .map((file) => ({ blob: file, name: pastedName(file.type) }));
}

export type ClipboardRead = { images: { blob: Blob; name: string }[]; unsupported: boolean };

/**
 * Кнопка «Вставить» (телефон, где нет ⌘V): Clipboard API читает картинки по нажатию — Safari
 * показывает свою кнопку «Вставить», Chrome спрашивает разрешение. Нет API — unsupported.
 */
export async function readClipboardImages(): Promise<ClipboardRead> {
  if (!navigator.clipboard || typeof navigator.clipboard.read !== "function") {
    return { images: [], unsupported: true };
  }
  const items = await navigator.clipboard.read();
  const images: { blob: Blob; name: string }[] = [];
  for (const item of items) {
    const type = item.types.find((value) => value.startsWith("image/"));
    if (!type) continue;
    images.push({ blob: await item.getType(type), name: pastedName(type) });
  }
  return { images, unsupported: false };
}

/**
 * Вставка картинок ⌘/Ctrl+V в любом месте экрана. Текст в полях вставляется как обычно —
 * перехватываются только картинки.
 */
export function usePasteImages(onImages: (images: { blob: Blob; name: string }[]) => void, enabled = true) {
  const handler = useRef(onImages);
  handler.current = onImages;
  useEffect(() => {
    if (!enabled) return;
    const onPaste = (event: ClipboardEvent) => {
      const images = imagesFrom(event.clipboardData);
      if (!images.length) return;
      event.preventDefault();
      handler.current(images);
    };
    window.addEventListener("paste", onPaste);
    return () => window.removeEventListener("paste", onPaste);
  }, [enabled]);
}
