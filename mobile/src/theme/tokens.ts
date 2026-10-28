// Сгенерировано scripts/gen_tokens.py из docs/design/lime-tech/tokens.json — не редактировать.
// Версия токенов: 1.6.0 (2026-10-28).

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

export type PaletteName = "lime" | "mint" | "sun" | "steel" | "graphite" | "olive" | "custom";
export type AccentName = "lime" | "mint" | "sun" | "sky" | "pink" | "lilac" | "steel" | "orange" | "olive" | "sand" | "navy" | "wine" | "graphite" | "forest";
export type PaletteGroup = "bright" | "calm" | "custom";

export type PaletteInfo = {
  key: PaletteName;
  name: string;
  group: PaletteGroup;
  note: string;
};

export type AccentInfo = {
  name: string;
  color: string;
  light: Partial<Palette>;
  dark: Partial<Palette>;
};

type ByTheme<T> = Record<ThemeName, T>;

/** Палитры покупателя по порядку показа (профиль, панель → «Тема»). */
export const paletteList: readonly PaletteInfo[] = [
  {
    "key": "lime",
    "name": "Лайм-тек",
    "group": "bright",
    "note": "Фирменная"
  },
  {
    "key": "mint",
    "name": "Мята",
    "group": "bright",
    "note": "Холоднее и спокойнее"
  },
  {
    "key": "sun",
    "name": "Солнце",
    "group": "bright",
    "note": "Тёплая"
  },
  {
    "key": "steel",
    "name": "Сталь",
    "group": "calm",
    "note": "Холодный синий, строгая"
  },
  {
    "key": "graphite",
    "name": "Графит",
    "group": "calm",
    "note": "Тёмно-серая с оранжевым"
  },
  {
    "key": "olive",
    "name": "Олива",
    "group": "calm",
    "note": "Хаки, «полевая»"
  },
  {
    "key": "custom",
    "name": "Своя",
    "group": "custom",
    "note": "Покупатель выбирает цвет акцента"
  }
];

/** Полные палитры обеих тем для каждой палитры покупателя. */
export const paletteThemes: Record<PaletteName, ByTheme<Palette>> = {
  "lime": {
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
  },
  "mint": {
    "light": {
      "bg": "#E6F2EC",
      "surface": "#FFFFFF",
      "ink": "#0F2A22",
      "muted": "#526861",
      "strike": "#7A8E87",
      "brand": "#17594A",
      "brandInk": "#5EE6A8",
      "accent": "#5EE6A8",
      "onAccent": "#0F2A22",
      "segOnBg": "#0F2A22",
      "segOnInk": "#5EE6A8",
      "tag": "#C4EBD3",
      "tagInk": "#17594A",
      "glass": "rgba(230,242,236,0.74)",
      "glassLine": "rgba(255,255,255,0.80)",
      "btnGlass": "rgba(255,255,255,0.82)",
      "nav": "#0F2A22",
      "navInk": "#9AA6A2",
      "navActiveInk": "#0F2A22",
      "ctaBg": "#0F2A22",
      "ctaInk": "#FFFFFF",
      "ctaFill": "#5EE6A8",
      "ctaDoneInk": "#0F2A22",
      "border": "#D3E0DA",
      "inputLine": "#C4D2CC",
      "neutral": "#526861",
      "neutralBg": "#DDEAE4",
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
      "bg": "#06100D",
      "surface": "#1E2D24",
      "ink": "#F0F2F1",
      "muted": "#AEB3B1",
      "strike": "#909594",
      "brand": "#5EE6A8",
      "brandInk": "#0F2A22",
      "accent": "#5EE6A8",
      "onAccent": "#0F2A22",
      "segOnBg": "#5EE6A8",
      "segOnInk": "#0F2A22",
      "tag": "#1D4A38",
      "tagInk": "#5EE6A8",
      "glass": "rgba(6,16,13,0.74)",
      "glassLine": "rgba(94,230,168,0.14)",
      "btnGlass": "rgba(30,45,36,0.85)",
      "nav": "#040B09",
      "navInk": "#7C817F",
      "navActiveInk": "#0F2A22",
      "ctaBg": "#5EE6A8",
      "ctaInk": "#0F2A22",
      "ctaFill": "#F0F2F1",
      "ctaDoneInk": "#0F2A22",
      "border": "#2E3932",
      "inputLine": "#434D47",
      "neutral": "#AEB3B1",
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
  },
  "sun": {
    "light": {
      "bg": "#F4F0E2",
      "surface": "#FFFFFF",
      "ink": "#2A220D",
      "muted": "#69624F",
      "strike": "#8F8978",
      "brand": "#6B4E0A",
      "brandInk": "#FFD23F",
      "accent": "#FFD23F",
      "onAccent": "#2A220D",
      "segOnBg": "#2A220D",
      "segOnInk": "#FFD23F",
      "tag": "#FFE38F",
      "tagInk": "#6B4E0A",
      "glass": "rgba(244,240,226,0.74)",
      "glassLine": "rgba(255,255,255,0.80)",
      "btnGlass": "rgba(255,255,255,0.82)",
      "nav": "#2A220D",
      "navInk": "#A3A097",
      "navActiveInk": "#2A220D",
      "ctaBg": "#2A220D",
      "ctaInk": "#FFFFFF",
      "ctaFill": "#FFD23F",
      "ctaDoneInk": "#2A220D",
      "border": "#E2DDCF",
      "inputLine": "#D4CFC0",
      "neutral": "#69624F",
      "neutralBg": "#ECE8D9",
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
      "bg": "#0E0C06",
      "surface": "#2D2A1E",
      "ink": "#F2F2F0",
      "muted": "#B2B2AE",
      "strike": "#959490",
      "brand": "#FFD23F",
      "brandInk": "#2A220D",
      "accent": "#FFD23F",
      "onAccent": "#2A220D",
      "segOnBg": "#FFD23F",
      "segOnInk": "#2A220D",
      "tag": "#4E4318",
      "tagInk": "#FFD23F",
      "glass": "rgba(14,12,6,0.74)",
      "glassLine": "rgba(255,210,63,0.14)",
      "btnGlass": "rgba(45,42,30,0.85)",
      "nav": "#0A0804",
      "navInk": "#83827F",
      "navActiveInk": "#2A220D",
      "ctaBg": "#FFD23F",
      "ctaInk": "#2A220D",
      "ctaFill": "#F2F2F0",
      "ctaDoneInk": "#2A220D",
      "border": "#39372F",
      "inputLine": "#4D4C45",
      "neutral": "#B2B2AE",
      "neutralBg": "#353226",
      "danger": "#FF9A8F",
      "dangerBg": "#3B1F1B",
      "success": "#A6E38A",
      "successBg": "#1C3522",
      "warning": "#FFCB6B",
      "warningBg": "#3A2E12",
      "info": "#9CCBFF",
      "infoBg": "#172A3D",
      "card": "#343022",
      "cardStops": [
        "#44402F",
        "#343022",
        "#24221A"
      ]
    }
  },
  "steel": {
    "light": {
      "bg": "#E6EBF0",
      "surface": "#FFFFFF",
      "ink": "#0E1A26",
      "muted": "#57616B",
      "strike": "#838B93",
      "brand": "#24476B",
      "brandInk": "#FFFFFF",
      "accent": "#7FA7CF",
      "onAccent": "#0E1A26",
      "segOnBg": "#0E1A26",
      "segOnInk": "#7FA7CF",
      "tag": "#D3E2F0",
      "tagInk": "#24476B",
      "glass": "rgba(230,235,240,0.74)",
      "glassLine": "rgba(255,255,255,0.80)",
      "btnGlass": "rgba(255,255,255,0.82)",
      "nav": "#0E1A26",
      "navInk": "#93989D",
      "navActiveInk": "#0E1A26",
      "ctaBg": "#0E1A26",
      "ctaInk": "#FFFFFF",
      "ctaFill": "#7FA7CF",
      "ctaDoneInk": "#0E1A26",
      "border": "#D3D8DE",
      "inputLine": "#C3CAD0",
      "neutral": "#57616B",
      "neutralBg": "#DDE3E8",
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
      "bg": "#070C12",
      "surface": "#1B2631",
      "ink": "#F0F1F2",
      "muted": "#A5A8AA",
      "strike": "#898C8F",
      "brand": "#7FA7CF",
      "brandInk": "#0E1A26",
      "accent": "#7FA7CF",
      "onAccent": "#0E1A26",
      "segOnBg": "#7FA7CF",
      "segOnInk": "#0E1A26",
      "tag": "#22384E",
      "tagInk": "#84ABD1",
      "glass": "rgba(7,12,18,0.74)",
      "glassLine": "rgba(127,167,207,0.14)",
      "btnGlass": "rgba(27,38,49,0.85)",
      "nav": "#05080D",
      "navInk": "#7F8184",
      "navActiveInk": "#0E1A26",
      "ctaBg": "#7FA7CF",
      "ctaInk": "#0E1A26",
      "ctaFill": "#F0F1F2",
      "ctaDoneInk": "#0E1A26",
      "border": "#2C343D",
      "inputLine": "#424951",
      "neutral": "#A5A8AA",
      "neutralBg": "#242E39",
      "danger": "#FF9A8F",
      "dangerBg": "#3B1F1B",
      "success": "#A6E38A",
      "successBg": "#1C3522",
      "warning": "#FFCB6B",
      "warningBg": "#3A2E12",
      "info": "#9CCBFF",
      "infoBg": "#172A3D",
      "card": "#1F2B38",
      "cardStops": [
        "#2B3A4B",
        "#1F2B38",
        "#161F29"
      ]
    }
  },
  "graphite": {
    "light": {
      "bg": "#E8EAED",
      "surface": "#FFFFFF",
      "ink": "#16191D",
      "muted": "#5D6064",
      "strike": "#878A8D",
      "brand": "#3A4049",
      "brandInk": "#FFFFFF",
      "accent": "#FF8A3D",
      "onAccent": "#16191D",
      "segOnBg": "#16191D",
      "segOnInk": "#FF8A3D",
      "tag": "#DADDE2",
      "tagInk": "#3A4049",
      "glass": "rgba(232,234,237,0.74)",
      "glassLine": "rgba(255,255,255,0.80)",
      "btnGlass": "rgba(255,255,255,0.82)",
      "nav": "#16191D",
      "navInk": "#969899",
      "navActiveInk": "#16191D",
      "ctaBg": "#16191D",
      "ctaInk": "#FFFFFF",
      "ctaFill": "#FF8A3D",
      "ctaDoneInk": "#16191D",
      "border": "#D5D7DA",
      "inputLine": "#C6C9CC",
      "neutral": "#5D6064",
      "neutralBg": "#E0E2E5",
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
      "bg": "#0B0C0E",
      "surface": "#212429",
      "ink": "#F1F1F2",
      "muted": "#A7A8A9",
      "strike": "#8A8A8B",
      "brand": "#FF8A3D",
      "brandInk": "#16191D",
      "accent": "#FF8A3D",
      "onAccent": "#16191D",
      "segOnBg": "#FF8A3D",
      "segOnInk": "#16191D",
      "tag": "#3A3F47",
      "tagInk": "#FF9956",
      "glass": "rgba(11,12,14,0.74)",
      "glassLine": "rgba(255,138,61,0.14)",
      "btnGlass": "rgba(33,36,41,0.85)",
      "nav": "#08080A",
      "navInk": "#7F7F80",
      "navActiveInk": "#16191D",
      "ctaBg": "#FF8A3D",
      "ctaInk": "#16191D",
      "ctaFill": "#F1F1F2",
      "ctaDoneInk": "#16191D",
      "border": "#303236",
      "inputLine": "#46474B",
      "neutral": "#A7A8A9",
      "neutralBg": "#292C31",
      "danger": "#FF9A8F",
      "dangerBg": "#3B1F1B",
      "success": "#A6E38A",
      "successBg": "#1C3522",
      "warning": "#FFCB6B",
      "warningBg": "#3A2E12",
      "info": "#9CCBFF",
      "infoBg": "#172A3D",
      "card": "#26292F",
      "cardStops": [
        "#34383F",
        "#26292F",
        "#1B1D21"
      ]
    }
  },
  "olive": {
    "light": {
      "bg": "#ECEEE2",
      "surface": "#FFFFFF",
      "ink": "#1B1F12",
      "muted": "#606357",
      "strike": "#888B7E",
      "brand": "#4B5320",
      "brandInk": "#FFFFFF",
      "accent": "#B5C267",
      "onAccent": "#1B1F12",
      "segOnBg": "#1B1F12",
      "segOnInk": "#B5C267",
      "tag": "#DDE3BF",
      "tagInk": "#4B5320",
      "glass": "rgba(236,238,226,0.74)",
      "glassLine": "rgba(255,255,255,0.80)",
      "btnGlass": "rgba(255,255,255,0.82)",
      "nav": "#1B1F12",
      "navInk": "#9B9C97",
      "navActiveInk": "#1B1F12",
      "ctaBg": "#1B1F12",
      "ctaInk": "#FFFFFF",
      "ctaFill": "#B5C267",
      "ctaDoneInk": "#1B1F12",
      "border": "#D9DBCF",
      "inputLine": "#CBCDC1",
      "neutral": "#606357",
      "neutralBg": "#E4E6DA",
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
      "bg": "#0B0D07",
      "surface": "#262A19",
      "ink": "#F1F2F0",
      "muted": "#AEB0AC",
      "strike": "#90928E",
      "brand": "#B5C267",
      "brandInk": "#1B1F12",
      "accent": "#B5C267",
      "onAccent": "#1B1F12",
      "segOnBg": "#B5C267",
      "segOnInk": "#1B1F12",
      "tag": "#3B4220",
      "tagInk": "#B5C267",
      "glass": "rgba(11,13,7,0.74)",
      "glassLine": "rgba(181,194,103,0.14)",
      "btnGlass": "rgba(38,42,25,0.85)",
      "nav": "#080905",
      "navInk": "#7F807D",
      "navActiveInk": "#1B1F12",
      "ctaBg": "#B5C267",
      "ctaInk": "#1B1F12",
      "ctaFill": "#F1F2F0",
      "ctaDoneInk": "#1B1F12",
      "border": "#34382B",
      "inputLine": "#494C41",
      "neutral": "#AEB0AC",
      "neutralBg": "#2E3222",
      "danger": "#FF9A8F",
      "dangerBg": "#3B1F1B",
      "success": "#A6E38A",
      "successBg": "#1C3522",
      "warning": "#FFCB6B",
      "warningBg": "#3A2E12",
      "info": "#9CCBFF",
      "infoBg": "#172A3D",
      "card": "#2B301D",
      "cardStops": [
        "#3A4128",
        "#2B301D",
        "#1F2315"
      ]
    }
  },
  "custom": {
    "light": {
      "bg": "#E8EBEE",
      "surface": "#FFFFFF",
      "ink": "#16191D",
      "muted": "#5D6064",
      "strike": "#878A8E",
      "brand": "#2A3038",
      "brandInk": "#7FA7CF",
      "accent": "#7FA7CF",
      "onAccent": "#16191D",
      "segOnBg": "#16191D",
      "segOnInk": "#7FA7CF",
      "tag": "#DADDE2",
      "tagInk": "#2A3038",
      "glass": "rgba(232,235,238,0.74)",
      "glassLine": "rgba(255,255,255,0.80)",
      "btnGlass": "rgba(255,255,255,0.82)",
      "nav": "#16191D",
      "navInk": "#969899",
      "navActiveInk": "#16191D",
      "ctaBg": "#16191D",
      "ctaInk": "#FFFFFF",
      "ctaFill": "#7FA7CF",
      "ctaDoneInk": "#16191D",
      "border": "#D5D8DB",
      "inputLine": "#C6C9CD",
      "neutral": "#5D6064",
      "neutralBg": "#E0E3E6",
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
      "bg": "#0A0C0F",
      "surface": "#202329",
      "ink": "#F1F1F1",
      "muted": "#A2A3A4",
      "strike": "#878889",
      "brand": "#7FA7CF",
      "brandInk": "#16191D",
      "accent": "#7FA7CF",
      "onAccent": "#16191D",
      "segOnBg": "#7FA7CF",
      "segOnInk": "#16191D",
      "tag": "#2E333B",
      "tagInk": "#7FA7CF",
      "glass": "rgba(10,12,15,0.74)",
      "glassLine": "rgba(127,167,207,0.14)",
      "btnGlass": "rgba(32,35,41,0.85)",
      "nav": "#07080A",
      "navInk": "#818182",
      "navActiveInk": "#16191D",
      "ctaBg": "#7FA7CF",
      "ctaInk": "#16191D",
      "ctaFill": "#F1F1F1",
      "ctaDoneInk": "#16191D",
      "border": "#303237",
      "inputLine": "#45474B",
      "neutral": "#A2A3A4",
      "neutralBg": "#282B31",
      "danger": "#FF9A8F",
      "dangerBg": "#3B1F1B",
      "success": "#A6E38A",
      "successBg": "#1C3522",
      "warning": "#FFCB6B",
      "warningBg": "#3A2E12",
      "info": "#9CCBFF",
      "infoBg": "#172A3D",
      "card": "#24282E",
      "cardStops": [
        "#30353D",
        "#24282E",
        "#1A1D22"
      ]
    }
  }
};

export const paletteShadows: Record<PaletteName, ByTheme<Shadows>> = {
  "lime": {
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
  },
  "mint": {
    "light": {
      "card": "0 1px 0 #FFFFFF inset, 0 3px 6px rgba(15,42,34,.10), 0 18px 30px -12px rgba(23,89,74,.48), 0 40px 60px -30px rgba(23,89,74,.55)",
      "control": "0 1px 0 #FFFFFF inset, 0 3px 5px rgba(15,42,34,.09), 0 14px 22px -10px rgba(23,89,74,.5)",
      "header": "0 1px 0 rgba(255,255,255,.9) inset, 0 22px 38px -18px rgba(23,89,74,.68)",
      "imageInset": "inset 0 -28px 46px -26px rgba(15,42,34,.32)",
      "nav": "0 22px 40px -14px rgba(15,42,34,.82)",
      "accentGlow": "0 10px 22px -6px rgba(94,230,168,.55)"
    },
    "dark": {
      "card": "0 1px 0 rgba(255,255,255,.22) inset, 0 0 0 1px rgba(255,255,255,.06) inset, 0 -3px 0 rgba(0,0,0,.38) inset, 0 0 0 1px rgba(94,230,168,.12), 0 0 26px -4px rgba(94,230,168,.22), 0 2px 4px rgba(0,0,0,.6), 0 14px 24px -10px rgba(0,0,0,.85), 0 34px 50px -24px rgba(0,0,0,.95)",
      "control": "0 1px 0 rgba(255,255,255,.13) inset, 0 0 0 1px rgba(255,255,255,.05) inset, 0 0 0 1px rgba(94,230,168,.10), 0 0 18px -4px rgba(94,230,168,.18), 0 2px 3px rgba(0,0,0,.55), 0 12px 22px -10px rgba(0,0,0,.85)",
      "header": "0 1px 0 rgba(255,255,255,.06) inset, 0 0 0 1px rgba(94,230,168,.10), 0 0 30px -8px rgba(94,230,168,.20), 0 22px 38px -14px rgba(0,0,0,.9)",
      "imageInset": "inset 0 1px 0 rgba(255,255,255,.18), inset 0 0 0 1px rgba(255,255,255,.05), inset 0 -34px 52px -26px rgba(0,0,0,.6), 0 10px 18px -12px rgba(0,0,0,.75)",
      "nav": "0 0 0 1px rgba(94,230,168,.16), 0 0 30px -6px rgba(94,230,168,.24), 0 22px 40px -14px rgba(0,0,0,.9)",
      "accentGlow": "0 10px 22px -6px rgba(94,230,168,.55)"
    }
  },
  "sun": {
    "light": {
      "card": "0 1px 0 #FFFFFF inset, 0 3px 6px rgba(42,34,13,.10), 0 18px 30px -12px rgba(107,78,10,.48), 0 40px 60px -30px rgba(107,78,10,.55)",
      "control": "0 1px 0 #FFFFFF inset, 0 3px 5px rgba(42,34,13,.09), 0 14px 22px -10px rgba(107,78,10,.5)",
      "header": "0 1px 0 rgba(255,255,255,.9) inset, 0 22px 38px -18px rgba(107,78,10,.68)",
      "imageInset": "inset 0 -28px 46px -26px rgba(42,34,13,.32)",
      "nav": "0 22px 40px -14px rgba(42,34,13,.82)",
      "accentGlow": "0 10px 22px -6px rgba(255,210,63,.55)"
    },
    "dark": {
      "card": "0 1px 0 rgba(255,255,255,.22) inset, 0 0 0 1px rgba(255,255,255,.06) inset, 0 -3px 0 rgba(0,0,0,.38) inset, 0 0 0 1px rgba(255,210,63,.12), 0 0 26px -4px rgba(255,210,63,.22), 0 2px 4px rgba(0,0,0,.6), 0 14px 24px -10px rgba(0,0,0,.85), 0 34px 50px -24px rgba(0,0,0,.95)",
      "control": "0 1px 0 rgba(255,255,255,.13) inset, 0 0 0 1px rgba(255,255,255,.05) inset, 0 0 0 1px rgba(255,210,63,.10), 0 0 18px -4px rgba(255,210,63,.18), 0 2px 3px rgba(0,0,0,.55), 0 12px 22px -10px rgba(0,0,0,.85)",
      "header": "0 1px 0 rgba(255,255,255,.06) inset, 0 0 0 1px rgba(255,210,63,.10), 0 0 30px -8px rgba(255,210,63,.20), 0 22px 38px -14px rgba(0,0,0,.9)",
      "imageInset": "inset 0 1px 0 rgba(255,255,255,.18), inset 0 0 0 1px rgba(255,255,255,.05), inset 0 -34px 52px -26px rgba(0,0,0,.6), 0 10px 18px -12px rgba(0,0,0,.75)",
      "nav": "0 0 0 1px rgba(255,210,63,.16), 0 0 30px -6px rgba(255,210,63,.24), 0 22px 40px -14px rgba(0,0,0,.9)",
      "accentGlow": "0 10px 22px -6px rgba(255,210,63,.55)"
    }
  },
  "steel": {
    "light": {
      "card": "0 1px 0 #FFFFFF inset, 0 3px 6px rgba(14,26,38,.10), 0 18px 30px -12px rgba(36,71,107,.48), 0 40px 60px -30px rgba(36,71,107,.55)",
      "control": "0 1px 0 #FFFFFF inset, 0 3px 5px rgba(14,26,38,.09), 0 14px 22px -10px rgba(36,71,107,.5)",
      "header": "0 1px 0 rgba(255,255,255,.9) inset, 0 22px 38px -18px rgba(36,71,107,.68)",
      "imageInset": "inset 0 -28px 46px -26px rgba(14,26,38,.32)",
      "nav": "0 22px 40px -14px rgba(14,26,38,.82)",
      "accentGlow": "0 10px 22px -6px rgba(127,167,207,.55)"
    },
    "dark": {
      "card": "0 1px 0 rgba(255,255,255,.22) inset, 0 0 0 1px rgba(255,255,255,.06) inset, 0 -3px 0 rgba(0,0,0,.38) inset, 0 0 0 1px rgba(127,167,207,.12), 0 0 26px -4px rgba(127,167,207,.22), 0 2px 4px rgba(0,0,0,.6), 0 14px 24px -10px rgba(0,0,0,.85), 0 34px 50px -24px rgba(0,0,0,.95)",
      "control": "0 1px 0 rgba(255,255,255,.13) inset, 0 0 0 1px rgba(255,255,255,.05) inset, 0 0 0 1px rgba(127,167,207,.10), 0 0 18px -4px rgba(127,167,207,.18), 0 2px 3px rgba(0,0,0,.55), 0 12px 22px -10px rgba(0,0,0,.85)",
      "header": "0 1px 0 rgba(255,255,255,.06) inset, 0 0 0 1px rgba(127,167,207,.10), 0 0 30px -8px rgba(127,167,207,.20), 0 22px 38px -14px rgba(0,0,0,.9)",
      "imageInset": "inset 0 1px 0 rgba(255,255,255,.18), inset 0 0 0 1px rgba(255,255,255,.05), inset 0 -34px 52px -26px rgba(0,0,0,.6), 0 10px 18px -12px rgba(0,0,0,.75)",
      "nav": "0 0 0 1px rgba(127,167,207,.16), 0 0 30px -6px rgba(127,167,207,.24), 0 22px 40px -14px rgba(0,0,0,.9)",
      "accentGlow": "0 10px 22px -6px rgba(127,167,207,.55)"
    }
  },
  "graphite": {
    "light": {
      "card": "0 1px 0 #FFFFFF inset, 0 3px 6px rgba(22,25,29,.10), 0 18px 30px -12px rgba(58,64,73,.48), 0 40px 60px -30px rgba(58,64,73,.55)",
      "control": "0 1px 0 #FFFFFF inset, 0 3px 5px rgba(22,25,29,.09), 0 14px 22px -10px rgba(58,64,73,.5)",
      "header": "0 1px 0 rgba(255,255,255,.9) inset, 0 22px 38px -18px rgba(58,64,73,.68)",
      "imageInset": "inset 0 -28px 46px -26px rgba(22,25,29,.32)",
      "nav": "0 22px 40px -14px rgba(22,25,29,.82)",
      "accentGlow": "0 10px 22px -6px rgba(255,138,61,.55)"
    },
    "dark": {
      "card": "0 1px 0 rgba(255,255,255,.22) inset, 0 0 0 1px rgba(255,255,255,.06) inset, 0 -3px 0 rgba(0,0,0,.38) inset, 0 0 0 1px rgba(255,138,61,.12), 0 0 26px -4px rgba(255,138,61,.22), 0 2px 4px rgba(0,0,0,.6), 0 14px 24px -10px rgba(0,0,0,.85), 0 34px 50px -24px rgba(0,0,0,.95)",
      "control": "0 1px 0 rgba(255,255,255,.13) inset, 0 0 0 1px rgba(255,255,255,.05) inset, 0 0 0 1px rgba(255,138,61,.10), 0 0 18px -4px rgba(255,138,61,.18), 0 2px 3px rgba(0,0,0,.55), 0 12px 22px -10px rgba(0,0,0,.85)",
      "header": "0 1px 0 rgba(255,255,255,.06) inset, 0 0 0 1px rgba(255,138,61,.10), 0 0 30px -8px rgba(255,138,61,.20), 0 22px 38px -14px rgba(0,0,0,.9)",
      "imageInset": "inset 0 1px 0 rgba(255,255,255,.18), inset 0 0 0 1px rgba(255,255,255,.05), inset 0 -34px 52px -26px rgba(0,0,0,.6), 0 10px 18px -12px rgba(0,0,0,.75)",
      "nav": "0 0 0 1px rgba(255,138,61,.16), 0 0 30px -6px rgba(255,138,61,.24), 0 22px 40px -14px rgba(0,0,0,.9)",
      "accentGlow": "0 10px 22px -6px rgba(255,138,61,.55)"
    }
  },
  "olive": {
    "light": {
      "card": "0 1px 0 #FFFFFF inset, 0 3px 6px rgba(27,31,18,.10), 0 18px 30px -12px rgba(75,83,32,.48), 0 40px 60px -30px rgba(75,83,32,.55)",
      "control": "0 1px 0 #FFFFFF inset, 0 3px 5px rgba(27,31,18,.09), 0 14px 22px -10px rgba(75,83,32,.5)",
      "header": "0 1px 0 rgba(255,255,255,.9) inset, 0 22px 38px -18px rgba(75,83,32,.68)",
      "imageInset": "inset 0 -28px 46px -26px rgba(27,31,18,.32)",
      "nav": "0 22px 40px -14px rgba(27,31,18,.82)",
      "accentGlow": "0 10px 22px -6px rgba(181,194,103,.55)"
    },
    "dark": {
      "card": "0 1px 0 rgba(255,255,255,.22) inset, 0 0 0 1px rgba(255,255,255,.06) inset, 0 -3px 0 rgba(0,0,0,.38) inset, 0 0 0 1px rgba(181,194,103,.12), 0 0 26px -4px rgba(181,194,103,.22), 0 2px 4px rgba(0,0,0,.6), 0 14px 24px -10px rgba(0,0,0,.85), 0 34px 50px -24px rgba(0,0,0,.95)",
      "control": "0 1px 0 rgba(255,255,255,.13) inset, 0 0 0 1px rgba(255,255,255,.05) inset, 0 0 0 1px rgba(181,194,103,.10), 0 0 18px -4px rgba(181,194,103,.18), 0 2px 3px rgba(0,0,0,.55), 0 12px 22px -10px rgba(0,0,0,.85)",
      "header": "0 1px 0 rgba(255,255,255,.06) inset, 0 0 0 1px rgba(181,194,103,.10), 0 0 30px -8px rgba(181,194,103,.20), 0 22px 38px -14px rgba(0,0,0,.9)",
      "imageInset": "inset 0 1px 0 rgba(255,255,255,.18), inset 0 0 0 1px rgba(255,255,255,.05), inset 0 -34px 52px -26px rgba(0,0,0,.6), 0 10px 18px -12px rgba(0,0,0,.75)",
      "nav": "0 0 0 1px rgba(181,194,103,.16), 0 0 30px -6px rgba(181,194,103,.24), 0 22px 40px -14px rgba(0,0,0,.9)",
      "accentGlow": "0 10px 22px -6px rgba(181,194,103,.55)"
    }
  },
  "custom": {
    "light": {
      "card": "0 1px 0 #FFFFFF inset, 0 3px 6px rgba(22,25,29,.10), 0 18px 30px -12px rgba(42,48,56,.48), 0 40px 60px -30px rgba(42,48,56,.55)",
      "control": "0 1px 0 #FFFFFF inset, 0 3px 5px rgba(22,25,29,.09), 0 14px 22px -10px rgba(42,48,56,.5)",
      "header": "0 1px 0 rgba(255,255,255,.9) inset, 0 22px 38px -18px rgba(42,48,56,.68)",
      "imageInset": "inset 0 -28px 46px -26px rgba(22,25,29,.32)",
      "nav": "0 22px 40px -14px rgba(22,25,29,.82)",
      "accentGlow": "0 10px 22px -6px rgba(127,167,207,.55)"
    },
    "dark": {
      "card": "0 1px 0 rgba(255,255,255,.22) inset, 0 0 0 1px rgba(255,255,255,.06) inset, 0 -3px 0 rgba(0,0,0,.38) inset, 0 0 0 1px rgba(127,167,207,.12), 0 0 26px -4px rgba(127,167,207,.22), 0 2px 4px rgba(0,0,0,.6), 0 14px 24px -10px rgba(0,0,0,.85), 0 34px 50px -24px rgba(0,0,0,.95)",
      "control": "0 1px 0 rgba(255,255,255,.13) inset, 0 0 0 1px rgba(255,255,255,.05) inset, 0 0 0 1px rgba(127,167,207,.10), 0 0 18px -4px rgba(127,167,207,.18), 0 2px 3px rgba(0,0,0,.55), 0 12px 22px -10px rgba(0,0,0,.85)",
      "header": "0 1px 0 rgba(255,255,255,.06) inset, 0 0 0 1px rgba(127,167,207,.10), 0 0 30px -8px rgba(127,167,207,.20), 0 22px 38px -14px rgba(0,0,0,.9)",
      "imageInset": "inset 0 1px 0 rgba(255,255,255,.18), inset 0 0 0 1px rgba(255,255,255,.05), inset 0 -34px 52px -26px rgba(0,0,0,.6), 0 10px 18px -12px rgba(0,0,0,.75)",
      "nav": "0 0 0 1px rgba(127,167,207,.16), 0 0 30px -6px rgba(127,167,207,.24), 0 22px 40px -14px rgba(0,0,0,.9)",
      "accentGlow": "0 10px 22px -6px rgba(127,167,207,.55)"
    }
  }
};

/** Акценты «Своей»: цвет, подпись и переопределения поверх paletteThemes.custom. */
export const accents: Record<AccentName, AccentInfo> = {
  "lime": {
    "name": "Лайм",
    "color": "#C6F432",
    "light": {
      "accent": "#C6F432",
      "onAccent": "#16191D",
      "navActiveInk": "#16191D",
      "ctaFill": "#C6F432",
      "ctaDoneInk": "#16191D",
      "brandInk": "#C6F432",
      "segOnBg": "#16191D",
      "segOnInk": "#C6F432"
    },
    "dark": {
      "accent": "#C6F432",
      "onAccent": "#16191D",
      "brand": "#C6F432",
      "brandInk": "#16191D",
      "segOnBg": "#C6F432",
      "segOnInk": "#16191D",
      "ctaBg": "#C6F432",
      "ctaInk": "#16191D",
      "navActiveInk": "#16191D",
      "glassLine": "rgba(198,244,50,0.14)"
    }
  },
  "mint": {
    "name": "Мята",
    "color": "#5EE6A8",
    "light": {
      "accent": "#5EE6A8",
      "onAccent": "#16191D",
      "navActiveInk": "#16191D",
      "ctaFill": "#5EE6A8",
      "ctaDoneInk": "#16191D",
      "brandInk": "#5EE6A8",
      "segOnBg": "#16191D",
      "segOnInk": "#5EE6A8"
    },
    "dark": {
      "accent": "#5EE6A8",
      "onAccent": "#16191D",
      "brand": "#5EE6A8",
      "brandInk": "#16191D",
      "segOnBg": "#5EE6A8",
      "segOnInk": "#16191D",
      "ctaBg": "#5EE6A8",
      "ctaInk": "#16191D",
      "navActiveInk": "#16191D",
      "glassLine": "rgba(94,230,168,0.14)"
    }
  },
  "sun": {
    "name": "Солнце",
    "color": "#FFD23F",
    "light": {
      "accent": "#FFD23F",
      "onAccent": "#16191D",
      "navActiveInk": "#16191D",
      "ctaFill": "#FFD23F",
      "ctaDoneInk": "#16191D",
      "brandInk": "#FFD23F",
      "segOnBg": "#16191D",
      "segOnInk": "#FFD23F"
    },
    "dark": {
      "accent": "#FFD23F",
      "onAccent": "#16191D",
      "brand": "#FFD23F",
      "brandInk": "#16191D",
      "segOnBg": "#FFD23F",
      "segOnInk": "#16191D",
      "ctaBg": "#FFD23F",
      "ctaInk": "#16191D",
      "navActiveInk": "#16191D",
      "glassLine": "rgba(255,210,63,0.14)"
    }
  },
  "sky": {
    "name": "Небо",
    "color": "#9CCBFF",
    "light": {
      "accent": "#9CCBFF",
      "onAccent": "#16191D",
      "navActiveInk": "#16191D",
      "ctaFill": "#9CCBFF",
      "ctaDoneInk": "#16191D",
      "brandInk": "#9CCBFF",
      "segOnBg": "#16191D",
      "segOnInk": "#9CCBFF"
    },
    "dark": {
      "accent": "#9CCBFF",
      "onAccent": "#16191D",
      "brand": "#9CCBFF",
      "brandInk": "#16191D",
      "segOnBg": "#9CCBFF",
      "segOnInk": "#16191D",
      "ctaBg": "#9CCBFF",
      "ctaInk": "#16191D",
      "navActiveInk": "#16191D",
      "glassLine": "rgba(156,203,255,0.14)"
    }
  },
  "pink": {
    "name": "Розовый",
    "color": "#FF9EC4",
    "light": {
      "accent": "#FF9EC4",
      "onAccent": "#16191D",
      "navActiveInk": "#16191D",
      "ctaFill": "#FF9EC4",
      "ctaDoneInk": "#16191D",
      "brandInk": "#FF9EC4",
      "segOnBg": "#16191D",
      "segOnInk": "#FF9EC4"
    },
    "dark": {
      "accent": "#FF9EC4",
      "onAccent": "#16191D",
      "brand": "#FF9EC4",
      "brandInk": "#16191D",
      "segOnBg": "#FF9EC4",
      "segOnInk": "#16191D",
      "ctaBg": "#FF9EC4",
      "ctaInk": "#16191D",
      "navActiveInk": "#16191D",
      "glassLine": "rgba(255,158,196,0.14)"
    }
  },
  "lilac": {
    "name": "Сирень",
    "color": "#B9A6FF",
    "light": {
      "accent": "#B9A6FF",
      "onAccent": "#16191D",
      "navActiveInk": "#16191D",
      "ctaFill": "#B9A6FF",
      "ctaDoneInk": "#16191D",
      "brandInk": "#B9A6FF",
      "segOnBg": "#16191D",
      "segOnInk": "#B9A6FF"
    },
    "dark": {
      "accent": "#B9A6FF",
      "onAccent": "#16191D",
      "brand": "#B9A6FF",
      "brandInk": "#16191D",
      "segOnBg": "#B9A6FF",
      "segOnInk": "#16191D",
      "ctaBg": "#B9A6FF",
      "ctaInk": "#16191D",
      "navActiveInk": "#16191D",
      "glassLine": "rgba(185,166,255,0.14)"
    }
  },
  "steel": {
    "name": "Сталь",
    "color": "#7FA7CF",
    "light": {
      "accent": "#7FA7CF",
      "onAccent": "#16191D",
      "navActiveInk": "#16191D",
      "ctaFill": "#7FA7CF",
      "ctaDoneInk": "#16191D",
      "brandInk": "#7FA7CF",
      "segOnBg": "#16191D",
      "segOnInk": "#7FA7CF"
    },
    "dark": {
      "accent": "#7FA7CF",
      "onAccent": "#16191D",
      "brand": "#7FA7CF",
      "brandInk": "#16191D",
      "segOnBg": "#7FA7CF",
      "segOnInk": "#16191D",
      "ctaBg": "#7FA7CF",
      "ctaInk": "#16191D",
      "navActiveInk": "#16191D",
      "glassLine": "rgba(127,167,207,0.14)"
    }
  },
  "orange": {
    "name": "Оранжевый",
    "color": "#FF8A3D",
    "light": {
      "accent": "#FF8A3D",
      "onAccent": "#16191D",
      "navActiveInk": "#16191D",
      "ctaFill": "#FF8A3D",
      "ctaDoneInk": "#16191D",
      "brandInk": "#FF8A3D",
      "segOnBg": "#16191D",
      "segOnInk": "#FF8A3D"
    },
    "dark": {
      "accent": "#FF8A3D",
      "onAccent": "#16191D",
      "brand": "#FF8A3D",
      "brandInk": "#16191D",
      "segOnBg": "#FF8A3D",
      "segOnInk": "#16191D",
      "ctaBg": "#FF8A3D",
      "ctaInk": "#16191D",
      "navActiveInk": "#16191D",
      "glassLine": "rgba(255,138,61,0.14)"
    }
  },
  "olive": {
    "name": "Олива",
    "color": "#B5C267",
    "light": {
      "accent": "#B5C267",
      "onAccent": "#16191D",
      "navActiveInk": "#16191D",
      "ctaFill": "#B5C267",
      "ctaDoneInk": "#16191D",
      "brandInk": "#B5C267",
      "segOnBg": "#16191D",
      "segOnInk": "#B5C267"
    },
    "dark": {
      "accent": "#B5C267",
      "onAccent": "#16191D",
      "brand": "#B5C267",
      "brandInk": "#16191D",
      "segOnBg": "#B5C267",
      "segOnInk": "#16191D",
      "ctaBg": "#B5C267",
      "ctaInk": "#16191D",
      "navActiveInk": "#16191D",
      "glassLine": "rgba(181,194,103,0.14)"
    }
  },
  "sand": {
    "name": "Песок",
    "color": "#C8B98A",
    "light": {
      "accent": "#C8B98A",
      "onAccent": "#16191D",
      "navActiveInk": "#16191D",
      "ctaFill": "#C8B98A",
      "ctaDoneInk": "#16191D",
      "brandInk": "#C8B98A",
      "segOnBg": "#16191D",
      "segOnInk": "#C8B98A"
    },
    "dark": {
      "accent": "#C8B98A",
      "onAccent": "#16191D",
      "brand": "#C8B98A",
      "brandInk": "#16191D",
      "segOnBg": "#C8B98A",
      "segOnInk": "#16191D",
      "ctaBg": "#C8B98A",
      "ctaInk": "#16191D",
      "navActiveInk": "#16191D",
      "glassLine": "rgba(200,185,138,0.14)"
    }
  },
  "navy": {
    "name": "Синий",
    "color": "#2F5D8A",
    "light": {
      "accent": "#2F5D8A",
      "onAccent": "#FFFFFF",
      "navActiveInk": "#FFFFFF",
      "ctaFill": "#2F5D8A",
      "ctaDoneInk": "#FFFFFF",
      "brandInk": "#FFFFFF",
      "segOnBg": "#2F5D8A",
      "segOnInk": "#FFFFFF"
    },
    "dark": {
      "accent": "#2F5D8A",
      "onAccent": "#FFFFFF",
      "brand": "#7492B1",
      "brandInk": "#16191D",
      "segOnBg": "#2F5D8A",
      "segOnInk": "#FFFFFF",
      "ctaBg": "#2F5D8A",
      "ctaInk": "#FFFFFF",
      "navActiveInk": "#FFFFFF",
      "glassLine": "rgba(47,93,138,0.14)"
    }
  },
  "wine": {
    "name": "Вино",
    "color": "#8E2C3E",
    "light": {
      "accent": "#8E2C3E",
      "onAccent": "#FFFFFF",
      "navActiveInk": "#FFFFFF",
      "ctaFill": "#8E2C3E",
      "ctaDoneInk": "#FFFFFF",
      "brandInk": "#FFFFFF",
      "segOnBg": "#8E2C3E",
      "segOnInk": "#FFFFFF"
    },
    "dark": {
      "accent": "#8E2C3E",
      "onAccent": "#FFFFFF",
      "brand": "#BB808B",
      "brandInk": "#16191D",
      "segOnBg": "#8E2C3E",
      "segOnInk": "#FFFFFF",
      "ctaBg": "#8E2C3E",
      "ctaInk": "#FFFFFF",
      "navActiveInk": "#FFFFFF",
      "glassLine": "rgba(142,44,62,0.14)"
    }
  },
  "graphite": {
    "name": "Графит",
    "color": "#3A4049",
    "light": {
      "accent": "#3A4049",
      "onAccent": "#FFFFFF",
      "navActiveInk": "#FFFFFF",
      "ctaFill": "#3A4049",
      "ctaDoneInk": "#FFFFFF",
      "brandInk": "#FFFFFF",
      "segOnBg": "#3A4049",
      "segOnInk": "#FFFFFF"
    },
    "dark": {
      "accent": "#3A4049",
      "onAccent": "#FFFFFF",
      "brand": "#8D9095",
      "brandInk": "#16191D",
      "segOnBg": "#3A4049",
      "segOnInk": "#FFFFFF",
      "ctaBg": "#3A4049",
      "ctaInk": "#FFFFFF",
      "navActiveInk": "#FFFFFF",
      "glassLine": "rgba(58,64,73,0.14)"
    }
  },
  "forest": {
    "name": "Изумруд",
    "color": "#1F7A5C",
    "light": {
      "accent": "#1F7A5C",
      "onAccent": "#FFFFFF",
      "navActiveInk": "#FFFFFF",
      "ctaFill": "#1F7A5C",
      "ctaDoneInk": "#FFFFFF",
      "brandInk": "#FFFFFF",
      "segOnBg": "#1F7A5C",
      "segOnInk": "#FFFFFF"
    },
    "dark": {
      "accent": "#1F7A5C",
      "onAccent": "#FFFFFF",
      "brand": "#599D86",
      "brandInk": "#16191D",
      "segOnBg": "#1F7A5C",
      "segOnInk": "#FFFFFF",
      "ctaBg": "#1F7A5C",
      "ctaInk": "#FFFFFF",
      "navActiveInk": "#FFFFFF",
      "glassLine": "rgba(31,122,92,0.14)"
    }
  }
};

export const accentShadows: Record<AccentName, ByTheme<Shadows>> = {
  "lime": {
    "light": {
      "card": "0 1px 0 #FFFFFF inset, 0 3px 6px rgba(22,25,29,.10), 0 18px 30px -12px rgba(42,48,56,.48), 0 40px 60px -30px rgba(42,48,56,.55)",
      "control": "0 1px 0 #FFFFFF inset, 0 3px 5px rgba(22,25,29,.09), 0 14px 22px -10px rgba(42,48,56,.5)",
      "header": "0 1px 0 rgba(255,255,255,.9) inset, 0 22px 38px -18px rgba(42,48,56,.68)",
      "imageInset": "inset 0 -28px 46px -26px rgba(22,25,29,.32)",
      "nav": "0 22px 40px -14px rgba(22,25,29,.82)",
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
  },
  "mint": {
    "light": {
      "card": "0 1px 0 #FFFFFF inset, 0 3px 6px rgba(22,25,29,.10), 0 18px 30px -12px rgba(42,48,56,.48), 0 40px 60px -30px rgba(42,48,56,.55)",
      "control": "0 1px 0 #FFFFFF inset, 0 3px 5px rgba(22,25,29,.09), 0 14px 22px -10px rgba(42,48,56,.5)",
      "header": "0 1px 0 rgba(255,255,255,.9) inset, 0 22px 38px -18px rgba(42,48,56,.68)",
      "imageInset": "inset 0 -28px 46px -26px rgba(22,25,29,.32)",
      "nav": "0 22px 40px -14px rgba(22,25,29,.82)",
      "accentGlow": "0 10px 22px -6px rgba(94,230,168,.55)"
    },
    "dark": {
      "card": "0 1px 0 rgba(255,255,255,.22) inset, 0 0 0 1px rgba(255,255,255,.06) inset, 0 -3px 0 rgba(0,0,0,.38) inset, 0 0 0 1px rgba(94,230,168,.12), 0 0 26px -4px rgba(94,230,168,.22), 0 2px 4px rgba(0,0,0,.6), 0 14px 24px -10px rgba(0,0,0,.85), 0 34px 50px -24px rgba(0,0,0,.95)",
      "control": "0 1px 0 rgba(255,255,255,.13) inset, 0 0 0 1px rgba(255,255,255,.05) inset, 0 0 0 1px rgba(94,230,168,.10), 0 0 18px -4px rgba(94,230,168,.18), 0 2px 3px rgba(0,0,0,.55), 0 12px 22px -10px rgba(0,0,0,.85)",
      "header": "0 1px 0 rgba(255,255,255,.06) inset, 0 0 0 1px rgba(94,230,168,.10), 0 0 30px -8px rgba(94,230,168,.20), 0 22px 38px -14px rgba(0,0,0,.9)",
      "imageInset": "inset 0 1px 0 rgba(255,255,255,.18), inset 0 0 0 1px rgba(255,255,255,.05), inset 0 -34px 52px -26px rgba(0,0,0,.6), 0 10px 18px -12px rgba(0,0,0,.75)",
      "nav": "0 0 0 1px rgba(94,230,168,.16), 0 0 30px -6px rgba(94,230,168,.24), 0 22px 40px -14px rgba(0,0,0,.9)",
      "accentGlow": "0 10px 22px -6px rgba(94,230,168,.55)"
    }
  },
  "sun": {
    "light": {
      "card": "0 1px 0 #FFFFFF inset, 0 3px 6px rgba(22,25,29,.10), 0 18px 30px -12px rgba(42,48,56,.48), 0 40px 60px -30px rgba(42,48,56,.55)",
      "control": "0 1px 0 #FFFFFF inset, 0 3px 5px rgba(22,25,29,.09), 0 14px 22px -10px rgba(42,48,56,.5)",
      "header": "0 1px 0 rgba(255,255,255,.9) inset, 0 22px 38px -18px rgba(42,48,56,.68)",
      "imageInset": "inset 0 -28px 46px -26px rgba(22,25,29,.32)",
      "nav": "0 22px 40px -14px rgba(22,25,29,.82)",
      "accentGlow": "0 10px 22px -6px rgba(255,210,63,.55)"
    },
    "dark": {
      "card": "0 1px 0 rgba(255,255,255,.22) inset, 0 0 0 1px rgba(255,255,255,.06) inset, 0 -3px 0 rgba(0,0,0,.38) inset, 0 0 0 1px rgba(255,210,63,.12), 0 0 26px -4px rgba(255,210,63,.22), 0 2px 4px rgba(0,0,0,.6), 0 14px 24px -10px rgba(0,0,0,.85), 0 34px 50px -24px rgba(0,0,0,.95)",
      "control": "0 1px 0 rgba(255,255,255,.13) inset, 0 0 0 1px rgba(255,255,255,.05) inset, 0 0 0 1px rgba(255,210,63,.10), 0 0 18px -4px rgba(255,210,63,.18), 0 2px 3px rgba(0,0,0,.55), 0 12px 22px -10px rgba(0,0,0,.85)",
      "header": "0 1px 0 rgba(255,255,255,.06) inset, 0 0 0 1px rgba(255,210,63,.10), 0 0 30px -8px rgba(255,210,63,.20), 0 22px 38px -14px rgba(0,0,0,.9)",
      "imageInset": "inset 0 1px 0 rgba(255,255,255,.18), inset 0 0 0 1px rgba(255,255,255,.05), inset 0 -34px 52px -26px rgba(0,0,0,.6), 0 10px 18px -12px rgba(0,0,0,.75)",
      "nav": "0 0 0 1px rgba(255,210,63,.16), 0 0 30px -6px rgba(255,210,63,.24), 0 22px 40px -14px rgba(0,0,0,.9)",
      "accentGlow": "0 10px 22px -6px rgba(255,210,63,.55)"
    }
  },
  "sky": {
    "light": {
      "card": "0 1px 0 #FFFFFF inset, 0 3px 6px rgba(22,25,29,.10), 0 18px 30px -12px rgba(42,48,56,.48), 0 40px 60px -30px rgba(42,48,56,.55)",
      "control": "0 1px 0 #FFFFFF inset, 0 3px 5px rgba(22,25,29,.09), 0 14px 22px -10px rgba(42,48,56,.5)",
      "header": "0 1px 0 rgba(255,255,255,.9) inset, 0 22px 38px -18px rgba(42,48,56,.68)",
      "imageInset": "inset 0 -28px 46px -26px rgba(22,25,29,.32)",
      "nav": "0 22px 40px -14px rgba(22,25,29,.82)",
      "accentGlow": "0 10px 22px -6px rgba(156,203,255,.55)"
    },
    "dark": {
      "card": "0 1px 0 rgba(255,255,255,.22) inset, 0 0 0 1px rgba(255,255,255,.06) inset, 0 -3px 0 rgba(0,0,0,.38) inset, 0 0 0 1px rgba(156,203,255,.12), 0 0 26px -4px rgba(156,203,255,.22), 0 2px 4px rgba(0,0,0,.6), 0 14px 24px -10px rgba(0,0,0,.85), 0 34px 50px -24px rgba(0,0,0,.95)",
      "control": "0 1px 0 rgba(255,255,255,.13) inset, 0 0 0 1px rgba(255,255,255,.05) inset, 0 0 0 1px rgba(156,203,255,.10), 0 0 18px -4px rgba(156,203,255,.18), 0 2px 3px rgba(0,0,0,.55), 0 12px 22px -10px rgba(0,0,0,.85)",
      "header": "0 1px 0 rgba(255,255,255,.06) inset, 0 0 0 1px rgba(156,203,255,.10), 0 0 30px -8px rgba(156,203,255,.20), 0 22px 38px -14px rgba(0,0,0,.9)",
      "imageInset": "inset 0 1px 0 rgba(255,255,255,.18), inset 0 0 0 1px rgba(255,255,255,.05), inset 0 -34px 52px -26px rgba(0,0,0,.6), 0 10px 18px -12px rgba(0,0,0,.75)",
      "nav": "0 0 0 1px rgba(156,203,255,.16), 0 0 30px -6px rgba(156,203,255,.24), 0 22px 40px -14px rgba(0,0,0,.9)",
      "accentGlow": "0 10px 22px -6px rgba(156,203,255,.55)"
    }
  },
  "pink": {
    "light": {
      "card": "0 1px 0 #FFFFFF inset, 0 3px 6px rgba(22,25,29,.10), 0 18px 30px -12px rgba(42,48,56,.48), 0 40px 60px -30px rgba(42,48,56,.55)",
      "control": "0 1px 0 #FFFFFF inset, 0 3px 5px rgba(22,25,29,.09), 0 14px 22px -10px rgba(42,48,56,.5)",
      "header": "0 1px 0 rgba(255,255,255,.9) inset, 0 22px 38px -18px rgba(42,48,56,.68)",
      "imageInset": "inset 0 -28px 46px -26px rgba(22,25,29,.32)",
      "nav": "0 22px 40px -14px rgba(22,25,29,.82)",
      "accentGlow": "0 10px 22px -6px rgba(255,158,196,.55)"
    },
    "dark": {
      "card": "0 1px 0 rgba(255,255,255,.22) inset, 0 0 0 1px rgba(255,255,255,.06) inset, 0 -3px 0 rgba(0,0,0,.38) inset, 0 0 0 1px rgba(255,158,196,.12), 0 0 26px -4px rgba(255,158,196,.22), 0 2px 4px rgba(0,0,0,.6), 0 14px 24px -10px rgba(0,0,0,.85), 0 34px 50px -24px rgba(0,0,0,.95)",
      "control": "0 1px 0 rgba(255,255,255,.13) inset, 0 0 0 1px rgba(255,255,255,.05) inset, 0 0 0 1px rgba(255,158,196,.10), 0 0 18px -4px rgba(255,158,196,.18), 0 2px 3px rgba(0,0,0,.55), 0 12px 22px -10px rgba(0,0,0,.85)",
      "header": "0 1px 0 rgba(255,255,255,.06) inset, 0 0 0 1px rgba(255,158,196,.10), 0 0 30px -8px rgba(255,158,196,.20), 0 22px 38px -14px rgba(0,0,0,.9)",
      "imageInset": "inset 0 1px 0 rgba(255,255,255,.18), inset 0 0 0 1px rgba(255,255,255,.05), inset 0 -34px 52px -26px rgba(0,0,0,.6), 0 10px 18px -12px rgba(0,0,0,.75)",
      "nav": "0 0 0 1px rgba(255,158,196,.16), 0 0 30px -6px rgba(255,158,196,.24), 0 22px 40px -14px rgba(0,0,0,.9)",
      "accentGlow": "0 10px 22px -6px rgba(255,158,196,.55)"
    }
  },
  "lilac": {
    "light": {
      "card": "0 1px 0 #FFFFFF inset, 0 3px 6px rgba(22,25,29,.10), 0 18px 30px -12px rgba(42,48,56,.48), 0 40px 60px -30px rgba(42,48,56,.55)",
      "control": "0 1px 0 #FFFFFF inset, 0 3px 5px rgba(22,25,29,.09), 0 14px 22px -10px rgba(42,48,56,.5)",
      "header": "0 1px 0 rgba(255,255,255,.9) inset, 0 22px 38px -18px rgba(42,48,56,.68)",
      "imageInset": "inset 0 -28px 46px -26px rgba(22,25,29,.32)",
      "nav": "0 22px 40px -14px rgba(22,25,29,.82)",
      "accentGlow": "0 10px 22px -6px rgba(185,166,255,.55)"
    },
    "dark": {
      "card": "0 1px 0 rgba(255,255,255,.22) inset, 0 0 0 1px rgba(255,255,255,.06) inset, 0 -3px 0 rgba(0,0,0,.38) inset, 0 0 0 1px rgba(185,166,255,.12), 0 0 26px -4px rgba(185,166,255,.22), 0 2px 4px rgba(0,0,0,.6), 0 14px 24px -10px rgba(0,0,0,.85), 0 34px 50px -24px rgba(0,0,0,.95)",
      "control": "0 1px 0 rgba(255,255,255,.13) inset, 0 0 0 1px rgba(255,255,255,.05) inset, 0 0 0 1px rgba(185,166,255,.10), 0 0 18px -4px rgba(185,166,255,.18), 0 2px 3px rgba(0,0,0,.55), 0 12px 22px -10px rgba(0,0,0,.85)",
      "header": "0 1px 0 rgba(255,255,255,.06) inset, 0 0 0 1px rgba(185,166,255,.10), 0 0 30px -8px rgba(185,166,255,.20), 0 22px 38px -14px rgba(0,0,0,.9)",
      "imageInset": "inset 0 1px 0 rgba(255,255,255,.18), inset 0 0 0 1px rgba(255,255,255,.05), inset 0 -34px 52px -26px rgba(0,0,0,.6), 0 10px 18px -12px rgba(0,0,0,.75)",
      "nav": "0 0 0 1px rgba(185,166,255,.16), 0 0 30px -6px rgba(185,166,255,.24), 0 22px 40px -14px rgba(0,0,0,.9)",
      "accentGlow": "0 10px 22px -6px rgba(185,166,255,.55)"
    }
  },
  "steel": {
    "light": {
      "card": "0 1px 0 #FFFFFF inset, 0 3px 6px rgba(22,25,29,.10), 0 18px 30px -12px rgba(42,48,56,.48), 0 40px 60px -30px rgba(42,48,56,.55)",
      "control": "0 1px 0 #FFFFFF inset, 0 3px 5px rgba(22,25,29,.09), 0 14px 22px -10px rgba(42,48,56,.5)",
      "header": "0 1px 0 rgba(255,255,255,.9) inset, 0 22px 38px -18px rgba(42,48,56,.68)",
      "imageInset": "inset 0 -28px 46px -26px rgba(22,25,29,.32)",
      "nav": "0 22px 40px -14px rgba(22,25,29,.82)",
      "accentGlow": "0 10px 22px -6px rgba(127,167,207,.55)"
    },
    "dark": {
      "card": "0 1px 0 rgba(255,255,255,.22) inset, 0 0 0 1px rgba(255,255,255,.06) inset, 0 -3px 0 rgba(0,0,0,.38) inset, 0 0 0 1px rgba(127,167,207,.12), 0 0 26px -4px rgba(127,167,207,.22), 0 2px 4px rgba(0,0,0,.6), 0 14px 24px -10px rgba(0,0,0,.85), 0 34px 50px -24px rgba(0,0,0,.95)",
      "control": "0 1px 0 rgba(255,255,255,.13) inset, 0 0 0 1px rgba(255,255,255,.05) inset, 0 0 0 1px rgba(127,167,207,.10), 0 0 18px -4px rgba(127,167,207,.18), 0 2px 3px rgba(0,0,0,.55), 0 12px 22px -10px rgba(0,0,0,.85)",
      "header": "0 1px 0 rgba(255,255,255,.06) inset, 0 0 0 1px rgba(127,167,207,.10), 0 0 30px -8px rgba(127,167,207,.20), 0 22px 38px -14px rgba(0,0,0,.9)",
      "imageInset": "inset 0 1px 0 rgba(255,255,255,.18), inset 0 0 0 1px rgba(255,255,255,.05), inset 0 -34px 52px -26px rgba(0,0,0,.6), 0 10px 18px -12px rgba(0,0,0,.75)",
      "nav": "0 0 0 1px rgba(127,167,207,.16), 0 0 30px -6px rgba(127,167,207,.24), 0 22px 40px -14px rgba(0,0,0,.9)",
      "accentGlow": "0 10px 22px -6px rgba(127,167,207,.55)"
    }
  },
  "orange": {
    "light": {
      "card": "0 1px 0 #FFFFFF inset, 0 3px 6px rgba(22,25,29,.10), 0 18px 30px -12px rgba(42,48,56,.48), 0 40px 60px -30px rgba(42,48,56,.55)",
      "control": "0 1px 0 #FFFFFF inset, 0 3px 5px rgba(22,25,29,.09), 0 14px 22px -10px rgba(42,48,56,.5)",
      "header": "0 1px 0 rgba(255,255,255,.9) inset, 0 22px 38px -18px rgba(42,48,56,.68)",
      "imageInset": "inset 0 -28px 46px -26px rgba(22,25,29,.32)",
      "nav": "0 22px 40px -14px rgba(22,25,29,.82)",
      "accentGlow": "0 10px 22px -6px rgba(255,138,61,.55)"
    },
    "dark": {
      "card": "0 1px 0 rgba(255,255,255,.22) inset, 0 0 0 1px rgba(255,255,255,.06) inset, 0 -3px 0 rgba(0,0,0,.38) inset, 0 0 0 1px rgba(255,138,61,.12), 0 0 26px -4px rgba(255,138,61,.22), 0 2px 4px rgba(0,0,0,.6), 0 14px 24px -10px rgba(0,0,0,.85), 0 34px 50px -24px rgba(0,0,0,.95)",
      "control": "0 1px 0 rgba(255,255,255,.13) inset, 0 0 0 1px rgba(255,255,255,.05) inset, 0 0 0 1px rgba(255,138,61,.10), 0 0 18px -4px rgba(255,138,61,.18), 0 2px 3px rgba(0,0,0,.55), 0 12px 22px -10px rgba(0,0,0,.85)",
      "header": "0 1px 0 rgba(255,255,255,.06) inset, 0 0 0 1px rgba(255,138,61,.10), 0 0 30px -8px rgba(255,138,61,.20), 0 22px 38px -14px rgba(0,0,0,.9)",
      "imageInset": "inset 0 1px 0 rgba(255,255,255,.18), inset 0 0 0 1px rgba(255,255,255,.05), inset 0 -34px 52px -26px rgba(0,0,0,.6), 0 10px 18px -12px rgba(0,0,0,.75)",
      "nav": "0 0 0 1px rgba(255,138,61,.16), 0 0 30px -6px rgba(255,138,61,.24), 0 22px 40px -14px rgba(0,0,0,.9)",
      "accentGlow": "0 10px 22px -6px rgba(255,138,61,.55)"
    }
  },
  "olive": {
    "light": {
      "card": "0 1px 0 #FFFFFF inset, 0 3px 6px rgba(22,25,29,.10), 0 18px 30px -12px rgba(42,48,56,.48), 0 40px 60px -30px rgba(42,48,56,.55)",
      "control": "0 1px 0 #FFFFFF inset, 0 3px 5px rgba(22,25,29,.09), 0 14px 22px -10px rgba(42,48,56,.5)",
      "header": "0 1px 0 rgba(255,255,255,.9) inset, 0 22px 38px -18px rgba(42,48,56,.68)",
      "imageInset": "inset 0 -28px 46px -26px rgba(22,25,29,.32)",
      "nav": "0 22px 40px -14px rgba(22,25,29,.82)",
      "accentGlow": "0 10px 22px -6px rgba(181,194,103,.55)"
    },
    "dark": {
      "card": "0 1px 0 rgba(255,255,255,.22) inset, 0 0 0 1px rgba(255,255,255,.06) inset, 0 -3px 0 rgba(0,0,0,.38) inset, 0 0 0 1px rgba(181,194,103,.12), 0 0 26px -4px rgba(181,194,103,.22), 0 2px 4px rgba(0,0,0,.6), 0 14px 24px -10px rgba(0,0,0,.85), 0 34px 50px -24px rgba(0,0,0,.95)",
      "control": "0 1px 0 rgba(255,255,255,.13) inset, 0 0 0 1px rgba(255,255,255,.05) inset, 0 0 0 1px rgba(181,194,103,.10), 0 0 18px -4px rgba(181,194,103,.18), 0 2px 3px rgba(0,0,0,.55), 0 12px 22px -10px rgba(0,0,0,.85)",
      "header": "0 1px 0 rgba(255,255,255,.06) inset, 0 0 0 1px rgba(181,194,103,.10), 0 0 30px -8px rgba(181,194,103,.20), 0 22px 38px -14px rgba(0,0,0,.9)",
      "imageInset": "inset 0 1px 0 rgba(255,255,255,.18), inset 0 0 0 1px rgba(255,255,255,.05), inset 0 -34px 52px -26px rgba(0,0,0,.6), 0 10px 18px -12px rgba(0,0,0,.75)",
      "nav": "0 0 0 1px rgba(181,194,103,.16), 0 0 30px -6px rgba(181,194,103,.24), 0 22px 40px -14px rgba(0,0,0,.9)",
      "accentGlow": "0 10px 22px -6px rgba(181,194,103,.55)"
    }
  },
  "sand": {
    "light": {
      "card": "0 1px 0 #FFFFFF inset, 0 3px 6px rgba(22,25,29,.10), 0 18px 30px -12px rgba(42,48,56,.48), 0 40px 60px -30px rgba(42,48,56,.55)",
      "control": "0 1px 0 #FFFFFF inset, 0 3px 5px rgba(22,25,29,.09), 0 14px 22px -10px rgba(42,48,56,.5)",
      "header": "0 1px 0 rgba(255,255,255,.9) inset, 0 22px 38px -18px rgba(42,48,56,.68)",
      "imageInset": "inset 0 -28px 46px -26px rgba(22,25,29,.32)",
      "nav": "0 22px 40px -14px rgba(22,25,29,.82)",
      "accentGlow": "0 10px 22px -6px rgba(200,185,138,.55)"
    },
    "dark": {
      "card": "0 1px 0 rgba(255,255,255,.22) inset, 0 0 0 1px rgba(255,255,255,.06) inset, 0 -3px 0 rgba(0,0,0,.38) inset, 0 0 0 1px rgba(200,185,138,.12), 0 0 26px -4px rgba(200,185,138,.22), 0 2px 4px rgba(0,0,0,.6), 0 14px 24px -10px rgba(0,0,0,.85), 0 34px 50px -24px rgba(0,0,0,.95)",
      "control": "0 1px 0 rgba(255,255,255,.13) inset, 0 0 0 1px rgba(255,255,255,.05) inset, 0 0 0 1px rgba(200,185,138,.10), 0 0 18px -4px rgba(200,185,138,.18), 0 2px 3px rgba(0,0,0,.55), 0 12px 22px -10px rgba(0,0,0,.85)",
      "header": "0 1px 0 rgba(255,255,255,.06) inset, 0 0 0 1px rgba(200,185,138,.10), 0 0 30px -8px rgba(200,185,138,.20), 0 22px 38px -14px rgba(0,0,0,.9)",
      "imageInset": "inset 0 1px 0 rgba(255,255,255,.18), inset 0 0 0 1px rgba(255,255,255,.05), inset 0 -34px 52px -26px rgba(0,0,0,.6), 0 10px 18px -12px rgba(0,0,0,.75)",
      "nav": "0 0 0 1px rgba(200,185,138,.16), 0 0 30px -6px rgba(200,185,138,.24), 0 22px 40px -14px rgba(0,0,0,.9)",
      "accentGlow": "0 10px 22px -6px rgba(200,185,138,.55)"
    }
  },
  "navy": {
    "light": {
      "card": "0 1px 0 #FFFFFF inset, 0 3px 6px rgba(22,25,29,.10), 0 18px 30px -12px rgba(42,48,56,.48), 0 40px 60px -30px rgba(42,48,56,.55)",
      "control": "0 1px 0 #FFFFFF inset, 0 3px 5px rgba(22,25,29,.09), 0 14px 22px -10px rgba(42,48,56,.5)",
      "header": "0 1px 0 rgba(255,255,255,.9) inset, 0 22px 38px -18px rgba(42,48,56,.68)",
      "imageInset": "inset 0 -28px 46px -26px rgba(22,25,29,.32)",
      "nav": "0 22px 40px -14px rgba(22,25,29,.82)",
      "accentGlow": "0 10px 22px -6px rgba(47,93,138,.55)"
    },
    "dark": {
      "card": "0 1px 0 rgba(255,255,255,.22) inset, 0 0 0 1px rgba(255,255,255,.06) inset, 0 -3px 0 rgba(0,0,0,.38) inset, 0 0 0 1px rgba(47,93,138,.12), 0 0 26px -4px rgba(47,93,138,.22), 0 2px 4px rgba(0,0,0,.6), 0 14px 24px -10px rgba(0,0,0,.85), 0 34px 50px -24px rgba(0,0,0,.95)",
      "control": "0 1px 0 rgba(255,255,255,.13) inset, 0 0 0 1px rgba(255,255,255,.05) inset, 0 0 0 1px rgba(47,93,138,.10), 0 0 18px -4px rgba(47,93,138,.18), 0 2px 3px rgba(0,0,0,.55), 0 12px 22px -10px rgba(0,0,0,.85)",
      "header": "0 1px 0 rgba(255,255,255,.06) inset, 0 0 0 1px rgba(47,93,138,.10), 0 0 30px -8px rgba(47,93,138,.20), 0 22px 38px -14px rgba(0,0,0,.9)",
      "imageInset": "inset 0 1px 0 rgba(255,255,255,.18), inset 0 0 0 1px rgba(255,255,255,.05), inset 0 -34px 52px -26px rgba(0,0,0,.6), 0 10px 18px -12px rgba(0,0,0,.75)",
      "nav": "0 0 0 1px rgba(47,93,138,.16), 0 0 30px -6px rgba(47,93,138,.24), 0 22px 40px -14px rgba(0,0,0,.9)",
      "accentGlow": "0 10px 22px -6px rgba(47,93,138,.55)"
    }
  },
  "wine": {
    "light": {
      "card": "0 1px 0 #FFFFFF inset, 0 3px 6px rgba(22,25,29,.10), 0 18px 30px -12px rgba(42,48,56,.48), 0 40px 60px -30px rgba(42,48,56,.55)",
      "control": "0 1px 0 #FFFFFF inset, 0 3px 5px rgba(22,25,29,.09), 0 14px 22px -10px rgba(42,48,56,.5)",
      "header": "0 1px 0 rgba(255,255,255,.9) inset, 0 22px 38px -18px rgba(42,48,56,.68)",
      "imageInset": "inset 0 -28px 46px -26px rgba(22,25,29,.32)",
      "nav": "0 22px 40px -14px rgba(22,25,29,.82)",
      "accentGlow": "0 10px 22px -6px rgba(142,44,62,.55)"
    },
    "dark": {
      "card": "0 1px 0 rgba(255,255,255,.22) inset, 0 0 0 1px rgba(255,255,255,.06) inset, 0 -3px 0 rgba(0,0,0,.38) inset, 0 0 0 1px rgba(142,44,62,.12), 0 0 26px -4px rgba(142,44,62,.22), 0 2px 4px rgba(0,0,0,.6), 0 14px 24px -10px rgba(0,0,0,.85), 0 34px 50px -24px rgba(0,0,0,.95)",
      "control": "0 1px 0 rgba(255,255,255,.13) inset, 0 0 0 1px rgba(255,255,255,.05) inset, 0 0 0 1px rgba(142,44,62,.10), 0 0 18px -4px rgba(142,44,62,.18), 0 2px 3px rgba(0,0,0,.55), 0 12px 22px -10px rgba(0,0,0,.85)",
      "header": "0 1px 0 rgba(255,255,255,.06) inset, 0 0 0 1px rgba(142,44,62,.10), 0 0 30px -8px rgba(142,44,62,.20), 0 22px 38px -14px rgba(0,0,0,.9)",
      "imageInset": "inset 0 1px 0 rgba(255,255,255,.18), inset 0 0 0 1px rgba(255,255,255,.05), inset 0 -34px 52px -26px rgba(0,0,0,.6), 0 10px 18px -12px rgba(0,0,0,.75)",
      "nav": "0 0 0 1px rgba(142,44,62,.16), 0 0 30px -6px rgba(142,44,62,.24), 0 22px 40px -14px rgba(0,0,0,.9)",
      "accentGlow": "0 10px 22px -6px rgba(142,44,62,.55)"
    }
  },
  "graphite": {
    "light": {
      "card": "0 1px 0 #FFFFFF inset, 0 3px 6px rgba(22,25,29,.10), 0 18px 30px -12px rgba(42,48,56,.48), 0 40px 60px -30px rgba(42,48,56,.55)",
      "control": "0 1px 0 #FFFFFF inset, 0 3px 5px rgba(22,25,29,.09), 0 14px 22px -10px rgba(42,48,56,.5)",
      "header": "0 1px 0 rgba(255,255,255,.9) inset, 0 22px 38px -18px rgba(42,48,56,.68)",
      "imageInset": "inset 0 -28px 46px -26px rgba(22,25,29,.32)",
      "nav": "0 22px 40px -14px rgba(22,25,29,.82)",
      "accentGlow": "0 10px 22px -6px rgba(58,64,73,.55)"
    },
    "dark": {
      "card": "0 1px 0 rgba(255,255,255,.22) inset, 0 0 0 1px rgba(255,255,255,.06) inset, 0 -3px 0 rgba(0,0,0,.38) inset, 0 0 0 1px rgba(58,64,73,.12), 0 0 26px -4px rgba(58,64,73,.22), 0 2px 4px rgba(0,0,0,.6), 0 14px 24px -10px rgba(0,0,0,.85), 0 34px 50px -24px rgba(0,0,0,.95)",
      "control": "0 1px 0 rgba(255,255,255,.13) inset, 0 0 0 1px rgba(255,255,255,.05) inset, 0 0 0 1px rgba(58,64,73,.10), 0 0 18px -4px rgba(58,64,73,.18), 0 2px 3px rgba(0,0,0,.55), 0 12px 22px -10px rgba(0,0,0,.85)",
      "header": "0 1px 0 rgba(255,255,255,.06) inset, 0 0 0 1px rgba(58,64,73,.10), 0 0 30px -8px rgba(58,64,73,.20), 0 22px 38px -14px rgba(0,0,0,.9)",
      "imageInset": "inset 0 1px 0 rgba(255,255,255,.18), inset 0 0 0 1px rgba(255,255,255,.05), inset 0 -34px 52px -26px rgba(0,0,0,.6), 0 10px 18px -12px rgba(0,0,0,.75)",
      "nav": "0 0 0 1px rgba(58,64,73,.16), 0 0 30px -6px rgba(58,64,73,.24), 0 22px 40px -14px rgba(0,0,0,.9)",
      "accentGlow": "0 10px 22px -6px rgba(58,64,73,.55)"
    }
  },
  "forest": {
    "light": {
      "card": "0 1px 0 #FFFFFF inset, 0 3px 6px rgba(22,25,29,.10), 0 18px 30px -12px rgba(42,48,56,.48), 0 40px 60px -30px rgba(42,48,56,.55)",
      "control": "0 1px 0 #FFFFFF inset, 0 3px 5px rgba(22,25,29,.09), 0 14px 22px -10px rgba(42,48,56,.5)",
      "header": "0 1px 0 rgba(255,255,255,.9) inset, 0 22px 38px -18px rgba(42,48,56,.68)",
      "imageInset": "inset 0 -28px 46px -26px rgba(22,25,29,.32)",
      "nav": "0 22px 40px -14px rgba(22,25,29,.82)",
      "accentGlow": "0 10px 22px -6px rgba(31,122,92,.55)"
    },
    "dark": {
      "card": "0 1px 0 rgba(255,255,255,.22) inset, 0 0 0 1px rgba(255,255,255,.06) inset, 0 -3px 0 rgba(0,0,0,.38) inset, 0 0 0 1px rgba(31,122,92,.12), 0 0 26px -4px rgba(31,122,92,.22), 0 2px 4px rgba(0,0,0,.6), 0 14px 24px -10px rgba(0,0,0,.85), 0 34px 50px -24px rgba(0,0,0,.95)",
      "control": "0 1px 0 rgba(255,255,255,.13) inset, 0 0 0 1px rgba(255,255,255,.05) inset, 0 0 0 1px rgba(31,122,92,.10), 0 0 18px -4px rgba(31,122,92,.18), 0 2px 3px rgba(0,0,0,.55), 0 12px 22px -10px rgba(0,0,0,.85)",
      "header": "0 1px 0 rgba(255,255,255,.06) inset, 0 0 0 1px rgba(31,122,92,.10), 0 0 30px -8px rgba(31,122,92,.20), 0 22px 38px -14px rgba(0,0,0,.9)",
      "imageInset": "inset 0 1px 0 rgba(255,255,255,.18), inset 0 0 0 1px rgba(255,255,255,.05), inset 0 -34px 52px -26px rgba(0,0,0,.6), 0 10px 18px -12px rgba(0,0,0,.75)",
      "nav": "0 0 0 1px rgba(31,122,92,.16), 0 0 30px -6px rgba(31,122,92,.24), 0 22px 40px -14px rgba(0,0,0,.9)",
      "accentGlow": "0 10px 22px -6px rgba(31,122,92,.55)"
    }
  }
};

/** Углы: множитель радиусов. Размер текста: множитель кегля (поверх системного). */
export const radiusScale = {
  "sharp": 0.6,
  "normal": 1,
  "soft": 1.35
} as const;

export type RadiusMode = keyof typeof radiusScale;

export const textScale = {
  "s": 1,
  "m": 1.15,
  "l": 1.3
} as const;

export type TextMode = keyof typeof textScale;

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
