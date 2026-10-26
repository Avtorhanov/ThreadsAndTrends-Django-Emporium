// Сгенерировано scripts/gen_tokens.py из docs/design/lime-tech/tokens.json — не редактировать.
// Версия токенов: 1.5.0 (2026-10-26).

export type ThemeName = "light" | "dark";

export type Palette = {
  accent: string;
  bg: string;
  border: string;
  brand: string;
  brandInk: string;
  btnGlass: string;
  card: string;
  cardStops: readonly [string, string, string] | null;
  ctaBg: string;
  ctaDoneInk: string;
  ctaFill: string;
  ctaInk: string;
  danger: string;
  dangerBg: string;
  glass: string;
  glassLine: string;
  info: string;
  infoBg: string;
  ink: string;
  inputLine: string;
  muted: string;
  nav: string;
  navActiveInk: string;
  navInk: string;
  neutral: string;
  neutralBg: string;
  onAccent: string;
  segOnBg: string;
  segOnInk: string;
  strike: string;
  success: string;
  successBg: string;
  surface: string;
  tag: string;
  tagInk: string;
  warning: string;
  warningBg: string;
};

export type Shadows = {
  accentGlow: string;
  card: string;
  control: string;
  header: string;
  imageInset: string;
  nav: string;
};

export const palettes: Record<ThemeName, Palette> = {
  "light": {
    "bg": "#EBF1E2",
    "surface": "#FFFFFF",
    "ink": "#13261C",
    "muted": "#4A5C51",
    "strike": "#5B6B60",
    "brand": "#1F4D3A",
    "brandInk": "#C6F432",
    "accent": "#C6F432",
    "onAccent": "#13261C",
    "segOnBg": "#13261C",
    "segOnInk": "#C6F432",
    "tag": "#DCE8CB",
    "tagInk": "#1F4D3A",
    "glass": "rgba(235,241,226,0.74)",
    "glassLine": "rgba(255,255,255,0.80)",
    "btnGlass": "rgba(255,255,255,0.82)",
    "nav": "#13261C",
    "navInk": "#B9C7BE",
    "navActiveInk": "#13261C",
    "ctaBg": "#13261C",
    "ctaInk": "#FFFFFF",
    "ctaFill": "#C6F432",
    "ctaDoneInk": "#13261C",
    "border": "#D6E0CB",
    "inputLine": "#C4D1B8",
    "neutral": "#4A5C51",
    "neutralBg": "#E3E9DC",
    "danger": "#B3261E",
    "dangerBg": "#FBE7E4",
    "success": "#24703F",
    "successBg": "#DFF2D2",
    "warning": "#8A5300",
    "warningBg": "#FFEFC7",
    "info": "#1E5FA6",
    "infoBg": "#E2EDF9",
    "card": "#FFFFFF",
    "cardStops": null
  },
  "dark": {
    "bg": "#070E0A",
    "surface": "#1F2E25",
    "ink": "#EEF5E9",
    "muted": "#AFC0B4",
    "strike": "#93A598",
    "brand": "#C6F432",
    "brandInk": "#13261C",
    "accent": "#C6F432",
    "onAccent": "#13261C",
    "segOnBg": "#C6F432",
    "segOnInk": "#13261C",
    "tag": "#22341A",
    "tagInk": "#D6F87A",
    "glass": "rgba(7,14,10,0.74)",
    "glassLine": "rgba(198,244,50,0.14)",
    "btnGlass": "rgba(31,46,37,0.85)",
    "nav": "#050A07",
    "navInk": "#8FA396",
    "navActiveInk": "#13261C",
    "ctaBg": "#C6F432",
    "ctaInk": "#13261C",
    "ctaFill": "#ECF3E7",
    "ctaDoneInk": "#13261C",
    "border": "#2B3C32",
    "inputLine": "#3B4F43",
    "neutral": "#AFC0B4",
    "neutralBg": "#26352C",
    "danger": "#FF9A8F",
    "dangerBg": "#3B1F1B",
    "success": "#A6E38A",
    "successBg": "#1C3522",
    "warning": "#FFCB6B",
    "warningBg": "#3A2E12",
    "info": "#9CCBFF",
    "infoBg": "#172A3D",
    "card": "#22342A",
    "cardStops": [
      "#2F4437",
      "#22342A",
      "#18241D"
    ]
  }
};

/** CSS box-shadow (несколько слоёв, inset) — стиль `boxShadow` React Native (новая архитектура). */
export const shadows: Record<ThemeName, Shadows> = {
  "light": {
    "card": "0 1px 0 #FFFFFF inset, 0 3px 6px rgba(19,38,28,.10), 0 18px 30px -12px rgba(31,77,58,.48), 0 40px 60px -30px rgba(31,77,58,.55)",
    "control": "0 1px 0 #FFFFFF inset, 0 3px 5px rgba(19,38,28,.09), 0 14px 22px -10px rgba(31,77,58,.5)",
    "header": "0 1px 0 rgba(255,255,255,.9) inset, 0 22px 38px -18px rgba(31,77,58,.68)",
    "imageInset": "inset 0 -28px 46px -26px rgba(19,38,28,.32)",
    "nav": "0 22px 40px -14px rgba(19,38,28,.82)",
    "accentGlow": "0 10px 22px -6px rgba(198,244,50,.55)"
  },
  "dark": {
    "card": "0 1px 0 rgba(255,255,255,.22) inset, 0 0 0 1px rgba(255,255,255,.06) inset, 0 -3px 0 rgba(0,0,0,.38) inset, 0 0 0 1px rgba(198,244,50,.12), 0 0 26px -4px rgba(198,244,50,.22), 0 2px 4px rgba(0,0,0,.6), 0 14px 24px -10px rgba(0,0,0,.85), 0 34px 50px -24px rgba(0,0,0,.95)",
    "control": "0 1px 0 rgba(255,255,255,.13) inset, 0 0 0 1px rgba(255,255,255,.05) inset, 0 0 0 1px rgba(198,244,50,.10), 0 0 18px -4px rgba(198,244,50,.18), 0 2px 3px rgba(0,0,0,.55), 0 12px 22px -10px rgba(0,0,0,.85)",
    "header": "0 1px 0 rgba(255,255,255,.06) inset, 0 0 0 1px rgba(198,244,50,.10), 0 0 30px -8px rgba(198,244,50,.20), 0 22px 38px -14px rgba(0,0,0,.9)",
    "imageInset": "inset 0 1px 0 rgba(255,255,255,.18), inset 0 0 0 1px rgba(255,255,255,.05), inset 0 -34px 52px -26px rgba(0,0,0,.6), 0 10px 18px -12px rgba(0,0,0,.75)",
    "nav": "0 0 0 1px rgba(198,244,50,.16), 0 0 30px -6px rgba(198,244,50,.24), 0 22px 40px -14px rgba(0,0,0,.9)",
    "accentGlow": "0 10px 22px -6px rgba(198,244,50,.55)"
  }
};

/** Фон плашки фото: [светлая тема, тёмная тема]. */
export const productTones = {
  "lime": [
    "#DDF38A",
    "#3F5416"
  ],
  "sun": [
    "#FFE38F",
    "#4E4318"
  ],
  "mint": [
    "#C4EBD3",
    "#1D4A38"
  ],
  "apricot": [
    "#FFD6B0",
    "#523820"
  ],
  "sage": [
    "#E7F5C2",
    "#354A20"
  ],
  "aqua": [
    "#D2EFE0",
    "#1F4636"
  ]
} as const;

export type ProductTone = keyof typeof productTones;

export const radius = {
  "badge": 6,
  "tag": 6,
  "seg": 10,
  "control": 12,
  "search": 13,
  "image": 14,
  "cta": 16,
  "card": 19,
  "nav": 21,
  "hero": 24,
  "sheet": 28
} as const;

export const space = {
  "feedSide": 10,
  "gridGap": 10,
  "cardPad": 6,
  "cardTextPad": 8,
  "headerSide": 18,
  "screen": 24
} as const;

export const size = {
  "touchMin": 44,
  "headerButton": 46,
  "headerButtonCompact": 38,
  "searchHeight": 52,
  "segHeight": 40,
  "cardImage": 214,
  "detailHero": 420,
  "navHeight": 52,
  "navActiveWidth": 124,
  "ctaHeight": 62
} as const;

export const font = {
  "display": {
    "family": "Unbounded",
    "weights": [
      500,
      700
    ],
    "use": "логотип, заголовки, цены"
  },
  "text": {
    "family": "Manrope",
    "weights": [
      500,
      600,
      700,
      800
    ],
    "use": "текст, кнопки, подписи"
  },
  "secondary": {
    "family": "Onest",
    "weights": [
      500,
      600
    ],
    "use": "вторичный текст: подвал, названия и описания в карточках, подсказки, крошки, старая цена"
  },
  "scale": {
    "wordmark": [
      24,
      16
    ],
    "h1": 28,
    "h2Detail": 23,
    "priceDetail": 24,
    "priceCard": 17,
    "cardTitle": 15,
    "body": 15,
    "button": 16,
    "tab": 13,
    "caption": 12
  }
} as const;

/** Кривые cubic-bezier(x1, y1, x2, y2) — для Easing.bezier. */
export const easing = {
  "easeOut": [
    0.2,
    0.8,
    0.2,
    1.0
  ],
  "easeSoft": [
    0.2,
    0.85,
    0.25,
    1.0
  ],
  "easeTab": [
    0.22,
    0.9,
    0.24,
    1.0
  ]
} as const;

export const motion = {
  "press": {
    "scale": 0.96,
    "ms": 180
  },
  "theme": {
    "ms": 450
  },
  "detailOpen": {
    "ms": 420,
    "hero": {
      "fromScale": 0.9,
      "ms": 550,
      "delay": 50
    },
    "stagger": [
      120,
      180,
      240,
      300
    ]
  },
  "listBehind": {
    "scale": 0.93,
    "opacity": 0.35,
    "blur": 1.5
  },
  "headerCollapse": {
    "ms": 400,
    "collapseAt": 24,
    "expandBelow": 8
  },
  "tabPill": {
    "ms": 400
  },
  "ctaFill": {
    "ms": 550,
    "direction": "left-to-right"
  }
} as const;
