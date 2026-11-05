import { useEffect, useRef, useState } from "react";

/** На сколько нужно потянуть (px после затухания), чтобы обновить. */
const THRESHOLD = 64;
const MAX_PULL = 96;
/** Индикатор крутится не меньше этого времени — иначе мелькает. */
const MIN_SPIN_MS = 600;

type Props = {
  /** Жест выключен (формы редактирования, открытая шторка меню). */
  disabled: boolean;
  /** Перезапросить данные экрана. */
  onRefresh: () => void;
};

/**
 * «Потяните, чтобы обновить» для телефона. Встроенная «резинка» страницы выключена
 * (overscroll-behavior в styles.css: иначе над шапкой открывается полоса фона), поэтому
 * жест свой: тянем вниз от самого верха — под шапкой выезжает индикатор, отпустили
 * за порогом — данные экрана перезапрашиваются без перезагрузки страницы.
 */
export function PullToRefresh({ disabled, onRefresh }: Props) {
  const [pull, setPull] = useState(0);
  const [spinning, setSpinning] = useState(false);
  const start = useRef<number | null>(null);
  const pullRef = useRef(0);
  const refreshRef = useRef(onRefresh);
  refreshRef.current = onRefresh;

  useEffect(() => {
    if (disabled || spinning) return;
    const reset = () => {
      start.current = null;
      pullRef.current = 0;
      setPull(0);
    };
    const onStart = (event: TouchEvent) => {
      const touch = event.touches[0];
      start.current = window.scrollY <= 0 && event.touches.length === 1 && touch ? touch.clientY : null;
    };
    const onMove = (event: TouchEvent) => {
      const touch = event.touches[0];
      if (start.current === null || !touch) return;
      const dy = touch.clientY - start.current;
      if (dy <= 0 || window.scrollY > 0) {
        if (pullRef.current) reset();
        return;
      }
      // Затухание: чем дальше тянем, тем медленнее едет индикатор.
      const value = Math.min(MAX_PULL, dy * 0.5);
      pullRef.current = value;
      setPull(value);
    };
    const onEnd = () => {
      if (start.current === null) return;
      const ready = pullRef.current >= THRESHOLD;
      reset();
      if (!ready) return;
      setSpinning(true);
      refreshRef.current();
      window.setTimeout(() => setSpinning(false), MIN_SPIN_MS);
    };
    window.addEventListener("touchstart", onStart, { passive: true });
    window.addEventListener("touchmove", onMove, { passive: true });
    window.addEventListener("touchend", onEnd);
    window.addEventListener("touchcancel", reset);
    return () => {
      window.removeEventListener("touchstart", onStart);
      window.removeEventListener("touchmove", onMove);
      window.removeEventListener("touchend", onEnd);
      window.removeEventListener("touchcancel", reset);
    };
  }, [disabled, spinning]);

  const offset = spinning ? THRESHOLD : pull;
  const progress = Math.min(1, pull / THRESHOLD);
  const visible = spinning || pull > 4;
  return (
    <div
      className={["ptr", spinning ? "is-spinning" : "", pull >= THRESHOLD ? "is-ready" : ""].filter(Boolean).join(" ")}
      style={{ transform: `translate(-50%, ${offset - 48}px)`, opacity: visible ? 1 : 0 }}
      role="status"
      aria-live="polite"
    >
      <svg viewBox="0 0 36 36" width="36" height="36" aria-hidden="true">
        <circle className="ptr-track" cx="18" cy="18" r="13" />
        <circle
          className="ptr-arc"
          cx="18"
          cy="18"
          r="13"
          pathLength={100}
          strokeDasharray={`${spinning ? 30 : Math.round(progress * 80)} 100`}
          style={spinning ? undefined : { transform: `rotate(${progress * 270 - 90}deg)` }}
        />
      </svg>
      <span className="sr-only">{spinning ? "Обновление…" : ""}</span>
    </div>
  );
}
