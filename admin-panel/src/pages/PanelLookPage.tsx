import { THEME_LABELS, type ThemeChoice, useTheme } from "../theme/theme";
import { PANEL_PALETTES } from "../theme/palettes";

/** Оформление самой панели: тема и палитра интерфейса. Хранится в этом браузере и не влияет
 * на магазин — вид витрины для покупателей задаётся в «Тема витрины». */
export function PanelLookPage() {
  const { choice, change, palette, changePalette } = useTheme();

  return (
    <section className="stack">
      <div className="page-header">
        <h1>Оформление панели</h1>
        <span className="muted small">Только для вас, в этом браузере</span>
      </div>

      <div className="card form-card">
        <h2>Тема</h2>
        <div className="seg-switch seg-switch-3" role="radiogroup" aria-label="Тема панели">
          {(Object.entries(THEME_LABELS) as [ThemeChoice, string][]).map(([value, label]) => (
            <button
              key={value}
              type="button"
              role="radio"
              aria-checked={choice === value}
              className={choice === value ? "is-on" : undefined}
              onClick={() => change(value)}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      <div className="card">
        <h2>Палитра</h2>
        <p className="muted small">Цвета меню, кнопок и отметок панели. Магазин не меняется.</p>
        <div className="panel-palettes" role="radiogroup" aria-label="Палитра панели">
          {PANEL_PALETTES.map((item) => (
            <button
              key={item.key}
              type="button"
              role="radio"
              aria-checked={palette === item.key}
              className={palette === item.key ? "panel-palette is-on" : "panel-palette"}
              onClick={() => changePalette(item.key)}
            >
              <span className="panel-palette-dots" aria-hidden="true">
                <i style={{ background: item.accent }} />
                <i style={{ background: item.brand }} />
                <i style={{ background: item.bg.light }} />
              </span>
              <span className="panel-palette-name">{item.name}</span>
            </button>
          ))}
        </div>
      </div>
    </section>
  );
}
