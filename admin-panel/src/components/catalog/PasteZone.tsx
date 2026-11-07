import { useEffect, useRef } from "react";

/**
 * Запасной путь вставки на телефоне: фото, скопированное в «Фото» iPhone, Safari часто не отдаёт
 * кнопке (Clipboard API), но отдаёт обычной вставке в поле. Поле без клавиатуры
 * (`inputMode="none"`): удержать палец → «Вставить» → событие paste ловит usePasteImages
 * (картинку в поле не вставляет). Текст, если вставили его, стирается.
 */
export function PasteZone({ onClose }: { onClose: () => void }) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    ref.current?.focus();
  }, []);

  return (
    <div className="paste-zone-wrap">
      <div
        ref={ref}
        className="paste-zone"
        contentEditable
        suppressContentEditableWarning
        inputMode="none"
        role="textbox"
        tabIndex={0}
        aria-label="Поле для вставки фото: удерживайте и выберите «Вставить»"
        data-placeholder="Удерживайте палец здесь → «Вставить»"
        onInput={(event) => {
          event.currentTarget.textContent = "";
        }}
      />
      <button type="button" className="paste-zone-close" aria-label="Закрыть поле вставки" onClick={onClose}>
        ×
      </button>
    </div>
  );
}
