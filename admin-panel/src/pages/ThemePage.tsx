import { useEffect, useState } from "react";

import { ApiError } from "../api/errors";
import { ScalePicker } from "../components/ScalePicker";
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
  TEXT_VALUES,
  themeService,
} from "../api/theme";
import { useLoader } from "../hooks/useCatalog";
import { setWordmark } from "../theme/wordmark";

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
    show_wordmark: state.show_wordmark,
    wordmark: state.wordmark,
  };
}

/** Слово рядом с «DiDi»: до 6 символов — как look.WORDMARK_MAX на сервере. */
const WORDMARK_MAX = 6;
// Место под слово в шапке витрины на узком телефоне (360 px) между «DiDi» и кнопками.
const WORDMARK_ROOM = 108;

/** Поместится ли слово в шапку узкого телефона: ширина шрифтом витрины (длинное — мельче, как в site.css). */
function wordmarkFits(word: string): boolean {
  const size = word.length >= 6 ? 20 : word.length === 5 ? 22 : 24;
  const family = getComputedStyle(document.documentElement).getPropertyValue("--font-display").trim() || "sans-serif";
  const context = document.createElement("canvas").getContext("2d");
  if (!context) return true;
  context.font = `700 ${size}px ${family}`;
  return context.measureText(word).width - 0.5 * word.length <= WORDMARK_ROOM; // letter-spacing −0,5 px
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
  const [wordDraft, setWordDraft] = useState("");

  useEffect(() => {
    if (loader.data) {
      setState(loader.data);
      setWordDraft(loader.data.wordmark);
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
      show_wordmark: next.show_wordmark ?? state.show_wordmark,
      wordmark: next.wordmark ?? state.wordmark,
    });
    setBusy(true);
    setError(null);
    setSaved(false);
    try {
      const result = await themeService.save(next);
      setState(result);
      setWordmark(result.show_wordmark, result.wordmark);
      setWordDraft(result.wordmark);
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
                <span>Масштаб, %</span>
                <ScalePicker
                  label="Масштаб по умолчанию"
                  values={TEXT_VALUES}
                  value={state.default_text}
                  disabled={busy}
                  onChange={(value) => void save({ default_text: value })}
                />
              </div>
              <p className="muted small">
                Действует у всех, кто не менял оформление в профиле. Ваш личный выбор в этом браузере
                сбрасывается при сохранении — витрина сразу показывает настройки магазина.
              </p>
            </div>

            <div className="card form-card">
              <h2>Логотип</h2>
              <label className="switch">
                <input
                  type="checkbox"
                  checked={state.show_wordmark}
                  disabled={busy}
                  onChange={(event) => void save({ show_wordmark: event.target.checked })}
                />
                <span className="switch-track" aria-hidden="true" />
                Слово рядом с «DiDi»
              </label>
              {state.show_wordmark ? (
                <form
                  className="wordmark-form"
                  onSubmit={(event) => {
                    event.preventDefault();
                    const word = wordDraft.trim().replace(/\s+/g, " ");
                    if (word && word !== state.wordmark) void save({ wordmark: word });
                  }}
                >
                  <span className="wordmark-input">
                    <input
                      value={wordDraft}
                      maxLength={WORDMARK_MAX}
                      aria-label="Слово рядом с «DiDi»"
                      aria-describedby="wordmark-hint"
                      onChange={(event) => setWordDraft(event.target.value)}
                    />
                    <span className="muted small" aria-hidden="true">
                      {wordDraft.length}/{WORDMARK_MAX}
                    </span>
                  </span>
                  <button
                    type="submit"
                    className="button button-accent"
                    disabled={busy || !wordDraft.trim() || wordDraft.trim() === state.wordmark}
                  >
                    Сохранить
                  </button>
                </form>
              ) : null}
              <p id="wordmark-hint" className="muted small">
                {state.show_wordmark && wordDraft.trim() && !wordmarkFits(wordDraft.trim())
                  ? "Широкие буквы: на узком телефоне слово обрежется — короче или уже буквы будет аккуратнее."
                  : `До ${WORDMARK_MAX} символов: буквы, цифры, пробел, дефис, точка, «&». В шапке сайта, в приложении и в панели; выключено — только плашка «DiDi».`}
              </p>
            </div>

            <div className="card form-card">
              <h2>Нижнее меню витрины</h2>
              <p className="muted small">
                Вкладки «Каталог · Контакты · Корзина · Профиль» на телефоне. Это вид для нового посетителя:
                покупатель может выбрать свой в профиле → «Оформление».
              </p>
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
                <ThemePreview palette={shown} dark={false} radius={state.default_radius} nav={state.nav_style} wordmark={state.show_wordmark ? state.wordmark : null} />
                <ThemePreview palette={shown} dark radius={state.default_radius} nav={state.nav_style} wordmark={state.show_wordmark ? state.wordmark : null} />
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

/** Фон меню в предпросмотре — как на витрине (site.css, data-nav). */
function navBackground(nav: ThemeNav, dark: boolean, surface: string): string {
  const navColor = dark ? "#050A07" : "#13261C";
  if (nav === "bar") return surface;
  if (nav === "glass") return dark ? "rgba(255,255,255,0.10)" : "rgba(255,255,255,0.55)";
  if (nav === "floating") return dark ? "rgba(5,10,7,0.78)" : "rgba(19,38,28,0.78)";
  return navColor;
}

function ThemePreview({
  palette,
  dark,
  radius,
  nav,
  wordmark,
}: {
  palette: ThemePalette;
  dark: boolean;
  radius: ThemeRadius;
  nav: ThemeNav;
  wordmark: string | null;
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
        {wordmark ? <strong style={{ color: dark ? palette.accent : palette.brand }}>{wordmark}</strong> : null}
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
        style={{ background: navBackground(nav, dark, surface), borderRadius: nav === "floating" || nav === "glass" ? r(16) : 0 }}
        aria-hidden="true"
      >
        {[0, 1, 2, 3].map((index) => (
          <i
            key={index}
            style={{
              background:
                index === 0
                  ? palette.accent
                  : nav === "bar" || nav === "glass"
                    ? dark
                      ? "rgba(255,255,255,0.2)"
                      : "rgba(0,0,0,0.14)"
                    : "rgba(255,255,255,0.22)",
              borderRadius: r(8),
            }}
          />
        ))}
      </span>
      <span className="muted small">{dark ? "Тёмная" : "Светлая"}</span>
    </div>
  );
}
