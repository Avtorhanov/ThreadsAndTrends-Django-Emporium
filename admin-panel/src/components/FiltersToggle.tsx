/** «Ещё фильтры» на телефоне: второстепенные фильтры (класс filters-extra) свёрнуты, чтобы список
 * начинался на первом экране. На компьютере кнопка скрыта и все фильтры видны (styles.css). */
export function FiltersToggle({ open, active, onToggle }: { open: boolean; active: number; onToggle: () => void }) {
  return (
    <button type="button" className="filters-toggle" aria-expanded={open} onClick={onToggle}>
      {open ? "Скрыть фильтры" : "Ещё фильтры"}
      {!open && active ? <span className="filters-count">{active}</span> : null}
    </button>
  );
}
