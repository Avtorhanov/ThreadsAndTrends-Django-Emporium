import { useEffect, useRef } from "react";

import { SHOE_CHART } from "./sizes";

/** Таблица размеров обуви: шторка снизу на телефоне, окно на компьютере (как PickSheet). */
export function SizeChartSheet({ onClose }: { onClose: () => void }) {
  const closeRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    closeRef.current?.focus();
    const close = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    document.addEventListener("keydown", close);
    return () => document.removeEventListener("keydown", close);
  }, [onClose]);

  return (
    <div className="sheet-layer">
      <button type="button" className="sheet-scrim" aria-label="Закрыть" onClick={onClose} />
      <div className="sheet" role="dialog" aria-modal="true" aria-labelledby="size-chart-title">
        <span className="sheet-grip" aria-hidden="true" />
        <h2 id="size-chart-title">Таблица размеров обуви</h2>
        <p className="muted small">Длина стопы — от пятки до большого пальца, стоя.</p>
        <table className="size-chart">
          <thead>
            <tr>
              <th scope="col">RU</th>
              <th scope="col">Стопа, см</th>
              <th scope="col">US жен.</th>
              <th scope="col">US муж.</th>
            </tr>
          </thead>
          <tbody>
            {SHOE_CHART.map((row) => (
              <tr key={row.ru}>
                <th scope="row">{row.ru}</th>
                <td>{row.cm}</td>
                <td>{row.women ?? "—"}</td>
                <td>{row.men ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <button ref={closeRef} type="button" className="button button-ghost" onClick={onClose}>
          Закрыть
        </button>
      </div>
    </div>
  );
}
