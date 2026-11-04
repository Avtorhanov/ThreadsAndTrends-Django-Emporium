// Сгенерировано scripts/gen_tokens.py из docs/design/lime-tech/tokens.json — не редактировать.

export type PanelPalette = "lime" | "mint" | "sun" | "steel" | "olive" | "custom";

export type PanelAccent = "lime" | "mint" | "sun" | "sky" | "pink" | "lilac" | "steel" | "orange" | "olive" | "sand" | "navy" | "wine" | "graphite" | "forest";

export type PanelRadius = "sharp" | "normal" | "soft";

export type PanelText = "s" | "m" | "l";

export type PanelPaletteInfo = {
  key: PanelPalette;
  name: string;
  accent: string;
  brand: string;
  bg: { light: string; dark: string };
};

export type PanelAccentInfo = {
  key: PanelAccent;
  name: string;
  color: string;
  on: string;
};

export const PANEL_PALETTES: readonly PanelPaletteInfo[] = [
  {
    "key": "lime",
    "name": "Лайм-тек",
    "accent": "#C6F432",
    "brand": "#1F4D3A",
    "bg": {
      "light": "#EBF1E2",
      "dark": "#070E0A"
    }
  },
  {
    "key": "mint",
    "name": "Мята",
    "accent": "#5EE6A8",
    "brand": "#17594A",
    "bg": {
      "light": "#E6F2EC",
      "dark": "#06100D"
    }
  },
  {
    "key": "sun",
    "name": "Солнце",
    "accent": "#FFD23F",
    "brand": "#6B4E0A",
    "bg": {
      "light": "#F4F0E2",
      "dark": "#0E0C06"
    }
  },
  {
    "key": "steel",
    "name": "Сталь",
    "accent": "#7FA7CF",
    "brand": "#24476B",
    "bg": {
      "light": "#E6EBF0",
      "dark": "#070C12"
    }
  },
  {
    "key": "olive",
    "name": "Олива",
    "accent": "#B5C267",
    "brand": "#4B5320",
    "bg": {
      "light": "#ECEEE2",
      "dark": "#0B0D07"
    }
  },
  {
    "key": "custom",
    "name": "Своя",
    "accent": "#7FA7CF",
    "brand": "#2A3038",
    "bg": {
      "light": "#E8EBEE",
      "dark": "#0A0C0F"
    }
  }
];

export const PANEL_ACCENTS: readonly PanelAccentInfo[] = [
  {
    "key": "lime",
    "name": "Лайм",
    "color": "#C6F432",
    "on": "#16191D"
  },
  {
    "key": "mint",
    "name": "Мята",
    "color": "#5EE6A8",
    "on": "#16191D"
  },
  {
    "key": "sun",
    "name": "Солнце",
    "color": "#FFD23F",
    "on": "#16191D"
  },
  {
    "key": "sky",
    "name": "Небо",
    "color": "#9CCBFF",
    "on": "#16191D"
  },
  {
    "key": "pink",
    "name": "Розовый",
    "color": "#FF9EC4",
    "on": "#16191D"
  },
  {
    "key": "lilac",
    "name": "Сирень",
    "color": "#B9A6FF",
    "on": "#16191D"
  },
  {
    "key": "steel",
    "name": "Сталь",
    "color": "#7FA7CF",
    "on": "#16191D"
  },
  {
    "key": "orange",
    "name": "Оранжевый",
    "color": "#FF8A3D",
    "on": "#16191D"
  },
  {
    "key": "olive",
    "name": "Олива",
    "color": "#B5C267",
    "on": "#16191D"
  },
  {
    "key": "sand",
    "name": "Песок",
    "color": "#C8B98A",
    "on": "#16191D"
  },
  {
    "key": "navy",
    "name": "Синий",
    "color": "#2F5D8A",
    "on": "#FFFFFF"
  },
  {
    "key": "wine",
    "name": "Вино",
    "color": "#8E2C3E",
    "on": "#FFFFFF"
  },
  {
    "key": "graphite",
    "name": "Графит",
    "color": "#3A4049",
    "on": "#FFFFFF"
  },
  {
    "key": "forest",
    "name": "Изумруд",
    "color": "#1F7A5C",
    "on": "#FFFFFF"
  }
];
