import Svg, { Circle, Path, Rect } from "react-native-svg";

/** Иконки макета «Лайм-тек» (контур 24×24, цвет — currentColor через prop color). */
export type IconName =
  | "grid"
  | "search"
  | "bag"
  | "user"
  | "sun"
  | "moon"
  | "back"
  | "close"
  | "filter"
  | "plus"
  | "minus"
  | "chevron"
  | "check"
  | "box";

type Props = { name: IconName; size?: number; color: string; strokeWidth?: number };

export function Icon({ name, size = 22, color, strokeWidth = 2 }: Props) {
  const common = {
    stroke: color,
    strokeWidth,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
    fill: "none",
  };
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24" accessible={false}>
      {name === "grid" ? (
        <>
          <Rect x={3} y={3} width={7} height={7} rx={2} {...common} />
          <Rect x={14} y={3} width={7} height={7} rx={2} {...common} />
          <Rect x={3} y={14} width={7} height={7} rx={2} {...common} />
          <Rect x={14} y={14} width={7} height={7} rx={2} {...common} />
        </>
      ) : null}
      {name === "search" ? (
        <>
          <Circle cx={11} cy={11} r={7} {...common} />
          <Path d="m20 20-3.5-3.5" {...common} />
        </>
      ) : null}
      {name === "bag" ? (
        <>
          <Path d="M5 8h14l-1 12H6L5 8Z" {...common} />
          <Path d="M9 8V6a3 3 0 0 1 6 0v2" {...common} />
        </>
      ) : null}
      {name === "user" ? (
        <>
          <Circle cx={12} cy={8} r={4} {...common} />
          <Path d="M4 21c1.5-4 4.5-6 8-6s6.5 2 8 6" {...common} />
        </>
      ) : null}
      {name === "sun" ? (
        <>
          <Circle cx={12} cy={12} r={4} {...common} />
          <Path
            d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"
            {...common}
          />
        </>
      ) : null}
      {name === "moon" ? <Path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5Z" {...common} /> : null}
      {name === "back" ? <Path d="M15 5l-7 7 7 7" {...common} /> : null}
      {name === "close" ? <Path d="M6 6l12 12M18 6 6 18" {...common} /> : null}
      {name === "filter" ? <Path d="M4 6h16M7 12h10M10 18h4" {...common} /> : null}
      {name === "plus" ? <Path d="M12 5v14M5 12h14" {...common} /> : null}
      {name === "minus" ? <Path d="M5 12h14" {...common} /> : null}
      {name === "chevron" ? <Path d="m9 5 7 7-7 7" {...common} /> : null}
      {name === "check" ? <Path d="m5 12.5 4.5 4.5L19 7" {...common} /> : null}
      {name === "box" ? (
        <>
          <Path d="M3 7.5 12 3l9 4.5v9L12 21l-9-4.5v-9Z" {...common} />
          <Path d="M3 7.5 12 12l9-4.5M12 12v9" {...common} />
        </>
      ) : null}
    </Svg>
  );
}
