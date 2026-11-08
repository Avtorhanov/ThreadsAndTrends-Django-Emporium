import type { IconName } from "../components/Icon";

/** Каналы согласования заказа (core.choices.AgreementChannel на сервере). */
export type AgreementChannel = "whatsapp" | "telegram" | "vk" | "phone";

export const AGREEMENT_CHANNELS: { id: AgreementChannel; label: string; icon: IconName; button: string }[] = [
  { id: "whatsapp", label: "WhatsApp", icon: "chat", button: "Написать в WhatsApp" },
  { id: "telegram", label: "Telegram", icon: "send", button: "Написать в Telegram" },
  { id: "vk", label: "ВКонтакте", icon: "customers", button: "Написать ВКонтакте" },
  { id: "phone", label: "Телефон", icon: "phone", button: "Позвонить продавцу" },
];

export function agreementChannel(id: string): (typeof AGREEMENT_CHANNELS)[number] | undefined {
  return AGREEMENT_CHANNELS.find((item) => item.id === id);
}
