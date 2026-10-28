import { useEffect, useState } from "react";

import { ApiError } from "../api/errors";
import {
  GROUP_TITLES,
  MODE_LABELS,
  NAV_HINTS,
  NAV_LABELS,
  type PaletteKey,
  RADIUS_LABELS,
  RADIUS_SCALE,
  type ThemeInput,
  type ThemeMode,
  type ThemeNav,
  type ThemePalette,
  type ThemeRadius,
  type ThemeState,
  type ThemeText,
  TEXT_LABELS,
  themeService,
} from "../api/theme";
import { useLoader } from "../hooks/useCatalog";

function message(error: unknown): string {
  if (!(error instanceof ApiError)) return "Не сохранено.";
  return Object.values(error.fieldErrors)[0]?.[0] ?? error.message;
}

function inputOf(state: ThemeState): ThemeInput {
  return {
    palettes: state.enabled,
    default_palette: state.default_palette,
    default_mode: state.default_mode,
    default_radius: state.default_radius,
    default_text: state.default_text,
    nav_style: state.nav_style,
  };
}

/**
 * Панель → «Тема»: какие палитры может выбрать покупатель, палитра, тема и углы для нового
 * посетителя. Изменения сохраняются сразу.
 */
export function ThemePage() {
  const loader = useLoader(() => themeService.get(), "theme", "Не удалось загрузить тему.");
  const [state, setState] = useState<ThemeState | null>(null);
  const [view, setView] = useState<PaletteKey | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (loader.data) {
      setState(loader.data);
      setView((prev) => prev ?? loader.data?.default_palette ?? null);
    }
  }, [loader.data]);

  async function save(changes: Partial<ThemeInput>) {
    if (!state) return;
    const previous = state;
    const next = { ...inputOf(state), ...changes };
    // Оптимистично: переключатель срабатывает сразу, при ошибке возвращается.
    setState({
      ...state,
      enabled: next.palettes,
      default_palette: next.default_palette,
      default_mode: next.default_mode,
      default_radius: next.default_radius,
      default_text: next.default_text ?? state.default_text,
      nav_style: next.nav_style ?? state.nav_style,
    });
    setBusy(true);
    setError(null);
    setSaved(false);
    try {
      setState(await themeService.save(next));
      setSaved(true);
    } catch (err) {
      setState(previous);
      setError(message(err));
    } finally {
      setBusy(false);
    }
  }

  function toggle(key: PaletteKey) {
    if (!state || key === state.default_palette) return;
    const enabled = state.enabled.includes(key)
      ? state.enabled.filter((item) => item !== key)
      : [...state.enabled, key];
    void save({ palettes: enabled });
  }

  const groups = state
    ? (Object.keys(GROUP_TITLES) as (keyof typeof GROUP_TITLES)[])
        .map((group) => ({ group, items: state.palettes.filter((item) => item.group === group) }))
        .filter((entry) => entry.items.length)
    : [];
  const shown = state?.palettes.find((item) => item.key === view) ?? null;

  return (
    <section className="stack">
      <div className="page-header">
        <h1>Тема для покупателей</h1>
        <span className="muted small">{busy ? "Сохраняем…" : saved ? "Сохранено" : "Изменения сохраняются сразу"}</span>
      </div>
      {loader.error ? <p className="alert">{loader.error}</p> : null}
      {error ? <p className="alert">{error}</p> : null}
      {loader.loading && !state ? <p className="muted">Загрузка…</p> : null}

      {state ? (
        <div className="theme-grid">
          <div className="stack">
            <div className="card">
              <h2>Палитры</h2>
              <p className="muted small">
                Выключенная палитра пропадает из профиля покупателя; у тех, кто её выбрал, — палитра по умолчанию.
              </p>
              {groups.map(({ group, items }) => (
                <div key={group} className="theme-group">
                  <h3>{GROUP_TITLES[group]}</h3>
                  <ul className="theme-rows">
                    {items.map((item) => (
                      <PaletteRow
                        key={item.key}
                        palette={item}
                        enabled={state.enabled.includes(item.key)}
                        isDefault={item.key === state.default_palette}
                        viewing={item.key === view}
                        busy={busy}
                        onView={() => setView(item.key)}
                        onToggle={() => toggle(item.key)}
                        onDefault={() => {
                          setView(item.key);
                          void save({
                            default_palette: item.key,
                            palettes: state.enabled.includes(item.key) ? state.enabled : [...state.enabled, item.key],
                          });
                        }}
                      />
                    ))}
                  </ul>
                </div>
              ))}
            </div>

            <div className="card form-card">
              <h2>Для нового посетителя</h2>
              <div className="field">
                <span>Тема</span>
                <div className="seg-switch seg-switch-3" role="radiogroup" aria-label="Тема по умолчанию">
                  {(Object.entries(MODE_LABELS) as [ThemeMode, string][]).map(([value, label]) => (
                    <button
                      key={value}
                      type="button"
                      role="radio"
                      aria-checked={state.default_mode === value}
                      className={state.default_mode === value ? "is-on" : undefined}
                      disabled={busy}
                      onClick={() => void save({ default_mode: value })}
                    >
                      {label}
                    </button>
                  ))}
                </div>
              </div>
              <div className="field">
                <span>Углы</span>
                <div className="seg-switch seg-switch-3" role="radiogroup" aria-label="Углы по умолчанию">
                  {(Object.entries(RADIUS_LABELS) as [ThemeRadius, string][]).map(([value, label]) => (
                    <button
                      key={value}
                      type="button"
                      role="radio"
                      aria-checked={state.default_radius === value}
                      className={state.default_radius === value ? "is-on" : undefined}
                      disabled={busy}
                      onClick={() => void save({ default_radius: value })}
                    >
                      <i className={`corner-mark corner-${value}`} aria-hidden="true" />
                      {label}
                    </button>
                  ))}
                </div>
              </div>
              <div className="field">
                <span>Размер текста</span>
                <div className="seg-switch seg-switch-3" role="radiogroup" aria-label="Размер текста по умолчанию">
                  {(Object.entries(TEXT_LABELS) as [ThemeText, string][]).map(([value, label]) => (
                    <button
                      key={value}
                      type="button"
                      role="radio"
                      aria-checked={state.default_text === value}
                      className={state.default_text === value ? "is-on" : undefined}
                      disabled={busy}
                      onClick={() => void save({ default_text: value })}
                    >
                      {label}
                    </button>
                  ))}
                </div>
              </div>
              <p className="muted small">
                Действует у всех, кто не менял оформление в профиле. Ваш личный выбор в этом браузере
                сбрасывается при сохранении — витрина сразу показывает настройки магазина.
              </p>
            </div>

            <div className="card form-card">
              <h2>Нижнее меню витрины</h2>
              <p className="muted small">Вкладки «Каталог · Контакты · Корзина · Профиль» на телефоне.</p>
              <div className="nav-options" role="radiogroup" aria-label="Вид нижнего меню">
                {(Object.keys(NAV_LABELS) as ThemeNav[]).map((value) => (
                  <button
                    key={value}
                    type="button"
                    role="radio"
                    aria-checked={state.nav_style === value}
                    className={state.nav_style === value ? "nav-option is-on" : "nav-option"}
                    disabled={busy}
                    onClick={() => void save({ nav_style: value })}
                  >
                    <NavSketch kind={value} />
                    <strong>{NAV_LABELS[value]}</strong>
                    <span className="muted small">{NAV_HINTS[value]}</span>
                  </button>
                ))}
              </div>
            </div>
          </div>

          {shown ? (
            <div className="card theme-preview-card">
              <h2>Предпросмотр: {shown.name}</h2>
              <div className="theme-previews">
                <ThemePreview palette={shown} dark={false} radius={state.default_radius} nav={state.nav_style} />
                <ThemePreview palette={shown} dark radius={state.default_radius} nav={state.nav_style} />
              </div>
              {shown.key === "custom" ? (
                <p className="muted small">«Своя»: покупатель выбирает акцент из {state.accents.length} проверенных цветов.</p>
              ) : null}
              <div className="theme-accents" aria-hidden={shown.key !== "custom"}>
                {shown.key === "custom"
                  ? state.accents.map((accent) => (
                      <span key={accent.key} title={accent.name} style={{ background: accent.color, color: accent.on }}>
                        Aa
                      </span>
                    ))
                  : null}
              </div>
            </div>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}

function PaletteRow(props: {
  palette: ThemePalette;
  enabled: boolean;
  isDefault: boolean;
  viewing: boolean;
  busy: boolean;
  onView: () => void;
  onToggle: () => void;
  onDefault: () => void;
}) {
  const { palette, enabled, isDefault, viewing, busy } = props;
  return (
    <li className={viewing ? "theme-row is-viewing" : "theme-row"}>
      <button type="button" className="theme-swatch" onClick={props.onView} aria-label={`Показать «${palette.name}»`}>
        <i style={{ background: palette.accent }} />
        <i style={{ background: palette.brand }} />
        <i style={{ background: palette.bg_light }} />
      </button>
      <span className="theme-row-text">
        <strong>{palette.name}</strong>
        <span className="muted small">{palette.note}</span>
      </span>
      {isDefault ? (
        <span className="badge badge-active">По умолчанию</span>
      ) : enabled ? (
        <button type="button" className="button button-ghost theme-default-btn" disabled={busy} onClick={props.onDefault}>
          Сделать основной
        </button>
      ) : null}
      <label className="switch" title={isDefault ? "Палитру по умолчанию нельзя выключить" : undefined}>
        <input
          type="checkbox"
          checked={enabled}
          disabled={busy || isDefault}
          onChange={props.onToggle}
          aria-label={`Доступна покупателям: ${palette.name}`}
        />
        <span className="switch-track" />
      </label>
    </li>
  );
}

/** Схема нижнего меню: полоса, капсула или панель с подписями. */
function NavSketch({ kind }: { kind: ThemeNav }) {
  return (
    <span className={`nav-sketch is-${kind}`} aria-hidden="true">
      <span className="nav-sketch-track">
        <i className="is-on" />
        <i />
        <i />
        <i />
      </span>
    </span>
  );
}

function ThemePreview({
  palette,
  dark,
  radius,
  nav,
}: {
  palette: ThemePalette;
  dark: boolean;
  radius: ThemeRadius;
  nav: ThemeNav;
}) {
  const k = RADIUS_SCALE[radius];
  const r = (value: number) => `${Math.round(value * k)}px`;
  const ink = dark ? "#EEF2EE" : "#16191D";
  const surface = dark ? "rgba(255,255,255,0.08)" : "#FFFFFF";
  return (
    <div
      className="theme-preview"
      style={{ background: dark ? palette.bg_dark : palette.bg_light, color: ink, borderRadius: r(22) }}
    >
      <div className="theme-preview-head">
        <span className="theme-preview-logo" style={{ background: dark ? palette.accent : palette.brand, color: dark ? "#16191D" : palette.accent, borderRadius: r(10) }}>
          DiDi
        </span>
        <strong style={{ color: dark ? palette.accent : palette.brand }}>shop</strong>
        <span className="theme-preview-btn" style={{ background: palette.accent, borderRadius: r(10) }} />
      </div>
      <div className="theme-preview-chips">
        <span style={{ background: palette.accent, color: "#16191D", borderRadius: r(9) }}>Все</span>
        <span style={{ background: surface, borderRadius: r(9) }}>Мужское</span>
        <span style={{ background: surface, borderRadius: r(9) }}>Женское</span>
      </div>
      <div className="theme-preview-item" style={{ background: surface, borderRadius: r(16) }}>
        <span className="theme-preview-photo" style={{ background: palette.accent, borderRadius: r(11), opacity: 0.35 }} />
        <span>
          <strong>Термос 591 мл</strong>
          <span>3 600 ₽</span>
        </span>
      </div>
      <span
        className={`theme-preview-nav theme-preview-nav-${nav}`}
        style={{
          background: nav === "bar" ? surface : dark ? "#050A07" : "#13261C",
          borderRadius: nav === "floating" ? r(16) : 0,
        }}
        aria-hidden="true"
      >
        {[0, 1, 2, 3].map((index) => (
          <i
            key={index}
            style={{
              background: index === 0 ? palette.accent : nav === "bar" ? (dark ? "rgba(255,255,255,0.2)" : "rgba(0,0,0,0.14)") : "rgba(255,255,255,0.22)",
              borderRadius: r(8),
            }}
          />
        ))}
      </span>
      <span className="muted small">{dark ? "Тёмная" : "Светлая"}</span>
    </div>
  );
}
