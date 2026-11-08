/**
 * Раскладка «Сводки»: порядок блоков и их размер — личный выбор сотрудника в этом браузере
 * (как оформление панели). Неизвестные и пропавшие блоки при чтении чинятся: новый блок
 * встаёт в конец, удалённый — убирается.
 */
export type WidgetId = "today" | "agreement" | "awaiting" | "assemble" | "deliver" | "turnover" | "recent" | "stock";
/** s — четверть ширины (на телефоне половина), m — половина (на телефоне вся), l — вся ширина. */
export type WidgetSize = "s" | "m" | "l";
export type SummaryLayout = { order: WidgetId[]; size: Record<WidgetId, WidgetSize> };

type Widget = { title: string; sizes: WidgetSize[]; size: WidgetSize };

export const WIDGETS: Record<WidgetId, Widget> = {
  today: { title: "Сегодня", sizes: ["s", "m", "l"], size: "s" },
  agreement: { title: "Ждут согласования", sizes: ["s", "m"], size: "s" },
  awaiting: { title: "Ждут оплаты", sizes: ["s", "m"], size: "s" },
  assemble: { title: "Собрать", sizes: ["s", "m"], size: "s" },
  deliver: { title: "Доставить", sizes: ["s", "m"], size: "s" },
  turnover: { title: "Оборот", sizes: ["m", "l"], size: "m" },
  recent: { title: "Заказы в работе", sizes: ["m", "l"], size: "m" },
  stock: { title: "Мало на складе", sizes: ["m", "l"], size: "l" },
};

// Пока онлайн-оплата не подключена, первым идёт «Ждут согласования», «Ждут оплаты» — ниже.
const ORDER: WidgetId[] = ["today", "agreement", "assemble", "deliver", "recent", "turnover", "awaiting", "stock"];
const KEY = "didi-panel-summary";

export function defaultLayout(): SummaryLayout {
  const size = {} as Record<WidgetId, WidgetSize>;
  for (const id of ORDER) size[id] = WIDGETS[id].size;
  return { order: [...ORDER], size };
}

function isWidget(value: unknown): value is WidgetId {
  return typeof value === "string" && value in WIDGETS;
}

export function loadLayout(): SummaryLayout {
  const layout = defaultLayout();
  try {
    const raw = JSON.parse(localStorage.getItem(KEY) ?? "null") as Partial<SummaryLayout> | null;
    if (!raw || typeof raw !== "object") return layout;
    const saved = Array.isArray(raw.order) ? raw.order.filter(isWidget) : [];
    const order = [...new Set(saved)];
    for (const id of ORDER) if (!order.includes(id)) order.push(id);
    layout.order = order;
    for (const id of ORDER) {
      const size = raw.size?.[id];
      if (size && WIDGETS[id].sizes.includes(size)) layout.size[id] = size;
    }
  } catch {
    // Нет хранилища или испорчено — раскладка по умолчанию.
  }
  return layout;
}

export function saveLayout(layout: SummaryLayout) {
  try {
    localStorage.setItem(KEY, JSON.stringify(layout));
  } catch {
    // Без хранилища раскладка живёт до перезагрузки.
  }
}
