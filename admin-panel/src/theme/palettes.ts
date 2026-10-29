// Сгенерировано scripts/gen_tokens.py из docs/design/lime-tech/tokens.json — не редактировать.

export type PanelPalette = "lime" | "mint" | "sun" | "steel" | "olive";

export type PanelPaletteInfo = {
  key: PanelPalette;
  name: string;
  accent: string;
  brand: string;
  bg: { light: string; dark: string };
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
  }
];
