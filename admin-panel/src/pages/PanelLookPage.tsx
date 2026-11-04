import { PANEL_ACCENTS, PANEL_PALETTES, type PanelRadius, type PanelText } from "../theme/palettes";
import { RADIUS_LABELS, TEXT_LABELS, THEME_LABELS, type ThemeChoice, useTheme } from "../theme/theme";

/** Сегментированный выбор из 3 вариантов. */
function Seg<T extends string>({
  label,
  labels,
  value,
  onChange,
}: {
  label: string;
  labels: Record<T, string>;
  value: T;
  onChange: (next: T) => void;
}) {
  return (
    <div className="seg-switch seg-switch-3" role="radiogroup" aria-label={label}>
      {(Object.entries(labels) as [T, string][]).map(([key, text]) => (
        <button
          key={key}
          type="button"
          role="radio"
          aria-checked={value === key}
          className={value === key ? "is-on" : undefined}
          onClick={() => onChange(key)}
        >
          {text}
        </button>
      ))}
    </div>
  );
}

/** Оформление самой панели: тема, палитра (со «Своей» и акцентом), углы и размер текста.
 * Хранится в этом браузере и не влияет на магазин — вид витрины задаётся в «Тема магазина». */
export function PanelLookPage() {
  const look = useTheme();

  return (
    <section className="stack">
      <div className="page-header">
        <h1>Оформление панели</h1>
        <span className="muted small">Только для вас, в этом браузере</span>
      </div>

      <div className="card form-card">
        <h2>Тема</h2>
        <Seg<ThemeChoice> label="Тема панели" labels={THEME_LABELS} value={look.choice} onChange={look.change} />
      </div>

      <div className="card">
        <h2>Палитра</h2>
        <p className="muted small">Цвета меню, кнопок и отметок панели. Магазин не меняется.</p>
        <div className="panel-palettes" role="radiogroup" aria-label="Палитра панели">
          {PANEL_PALETTES.map((item) => {
            const custom = item.key === "custom";
            const accent = custom
              ? (PANEL_ACCENTS.find((a) => a.key === look.accent)?.color ?? item.accent)
              : item.accent;
            return (
              <button
                key={item.key}
                type="button"
                role="radio"
                aria-checked={look.palette === item.key}
                className={look.palette === item.key ? "panel-palette is-on" : "panel-palette"}
                onClick={() => look.changePalette(item.key)}
              >
                <span className="panel-palette-dots" aria-hidden="true">
                  <i style={{ background: accent }} />
                  <i style={{ background: item.brand }} />
                  <i style={{ background: item.bg.light }} />
                </span>
                <span className="panel-palette-name">{item.name}</span>
              </button>
            );
          })}
        </div>

        {look.palette === "custom" ? (
          <div className="panel-accents-wrap">
            <h3 className="small-title">Акцент «Своей»</h3>
            <div className="panel-accents" role="radiogroup" aria-label="Акцент палитры «Своя»">
              {PANEL_ACCENTS.map((item) => (
                <button
                  key={item.key}
                  type="button"
                  role="radio"
                  aria-checked={look.accent === item.key}
                  aria-label={item.name}
                  title={item.name}
                  className={look.accent === item.key ? "panel-accent is-on" : "panel-accent"}
                  style={{ background: item.color, color: item.on }}
                  onClick={() => look.changeAccent(item.key)}
                >
                  {look.accent === item.key ? "✓" : ""}
                </button>
              ))}
            </div>
          </div>
        ) : null}
      </div>

      <div className="card form-card">
        <h2>Углы</h2>
        <Seg<PanelRadius> label="Углы" labels={RADIUS_LABELS} value={look.radius} onChange={look.changeRadius} />
        <h2>Размер текста</h2>
        <Seg<PanelText> label="Размер текста" labels={TEXT_LABELS} value={look.text} onChange={look.changeText} />
      </div>

      <div>
        <button type="button" className="button button-ghost" onClick={look.reset}>
          Вернуть как было
        </button>
      </div>
    </section>
  );
}
