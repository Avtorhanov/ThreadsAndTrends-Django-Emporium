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
  | "box"
  | "chat"
  | "send"
  | "people"
  | "phone"
  | "mail"
  | "help";

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
      {name === "chat" ? (
        <>
          <Path d="M4 20l1.3-3.9A8 8 0 1 1 8 19.1L4 20Z" {...common} />
          <Path
            d="M9.5 9.5c.3 1.8 2.2 3.8 4 4.2l1.1-1.1 1.9.8-.3 1.3c-3 .4-7.5-4-7-7l1.3-.3.8 1.9-1 1.2"
            {...common}
          />
        </>
      ) : null}
      {name === "send" ? (
        <>
          <Path d="M21 3 3 10.5l7 2.5 2.5 7L21 3Z" {...common} />
          <Path d="m10 13 4.5-4.5" {...common} />
        </>
      ) : null}
      {name === "people" ? (
        <>
          <Circle cx={9} cy={8} r={3.5} {...common} />
          <Path d="M2.5 20c1-3.5 3.5-5.5 6.5-5.5s5.5 2 6.5 5.5" {...common} />
          <Path d="M16 4.6a3.5 3.5 0 0 1 0 6.8M18 14.8c1.7.8 2.9 2.5 3.5 5.2" {...common} />
        </>
      ) : null}
      {name === "phone" ? (
        <Path
          d="M5 3h3.5l1.5 4.5-2.2 1.4a11 11 0 0 0 5.3 5.3l1.4-2.2L19 13.5V17a2 2 0 0 1-2 2A14 14 0 0 1 3 5a2 2 0 0 1 2-2Z"
          {...common}
        />
      ) : null}
      {name === "mail" ? (
        <>
          <Rect x={3} y={5} width={18} height={14} rx={3} {...common} />
          <Path d="m4 7 8 6 8-6" {...common} />
        </>
      ) : null}
      {name === "help" ? (
        <>
          <Circle cx={12} cy={12} r={9} {...common} />
          <Path d="M9.5 9.5a2.5 2.5 0 0 1 4.8 1c0 1.7-2.3 2-2.3 3.5M12 17h.01" {...common} />
        </>
      ) : null}
      {name === "box" ? (
        <>
          <Path d="M3 7.5 12 3l9 4.5v9L12 21l-9-4.5v-9Z" {...common} />
          <Path d="M3 7.5 12 12l9-4.5M12 12v9" {...common} />
        </>
      ) : null}
    </Svg>
  );
}
