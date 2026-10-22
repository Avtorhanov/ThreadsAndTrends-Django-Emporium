import { type ProductTone, productTones } from "./tokens";

const TONES = Object.keys(productTones) as ProductTone[];

/** Тон плашки фото — стабильно по slug товара (FNV-1a), без поля в БД. */
export function toneFor(slug: string): ProductTone {
  let hash = 0x811c9dc5;
  for (let i = 0; i < slug.length; i += 1) {
    hash ^= slug.charCodeAt(i);
    hash = Math.imul(hash, 0x01000193);
  }
  return TONES[(hash >>> 0) % TONES.length] ?? "lime";
}

export function toneColor(slug: string, dark: boolean): string {
  return productTones[toneFor(slug)][dark ? 1 : 0];
}
