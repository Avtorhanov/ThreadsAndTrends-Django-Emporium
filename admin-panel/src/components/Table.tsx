import { type ReactNode, useLayoutEffect, useRef } from "react";

/** Таблица панели. На широком экране — обычная таблица; на телефоне CSS превращает строки
 * в карточки, а подпись каждой ячейки берётся из заголовка её колонки (data-label).
 * Подписи проставляются здесь, чтобы страницы не дублировали заголовки в каждой ячейке. */
export function Table({ loading = false, children }: { loading?: boolean; children: ReactNode }) {
  const ref = useRef<HTMLTableElement>(null);

  useLayoutEffect(() => {
    const table = ref.current;
    if (!table) return;
    const label = () => {
      const heads = Array.from(table.querySelectorAll("thead th")).map(
        (th) => th.textContent?.trim() ?? "",
      );
      table.querySelectorAll("tbody tr").forEach((row) => {
        const cells = Array.from(row.children) as HTMLElement[];
        // Строки с объединёнными ячейками (пусто, итоги) подписей не получают.
        if (cells.some((cell) => (cell as HTMLTableCellElement).colSpan > 1)) return;
        cells.forEach((cell, index) => {
          const text = heads[index] ?? "";
          if (cell.dataset.label !== text) cell.dataset.label = text;
        });
      });
    };
    label();
    const observer = new MutationObserver(label);
    observer.observe(table, { childList: true, subtree: true });
    return () => observer.disconnect();
  }, []);

  return (
    <div className="table-wrap">
      <table ref={ref} className={loading ? "table is-loading" : "table"}>
        {children}
      </table>
    </div>
  );
}
