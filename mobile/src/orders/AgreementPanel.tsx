import { Linking, Share, Text } from "react-native";

import { Button, Card } from "../components/ui";
import { fonts } from "../theme/fonts";
import { makeStyles } from "../theme/ThemeProvider";
import { radius } from "../theme/tokens";
import { formatDateTime } from "./components";
import type { OrderDetail } from "./orderService";

const BUTTONS = {
  whatsapp: "Написать в WhatsApp",
  telegram: "Написать в Telegram",
  vk: "Написать ВКонтакте",
  phone: "Позвонить продавцу",
} as const;

/**
 * Заказ «по согласованию»: покупатель пишет продавцу готовым текстом (номер заказа, товары, сумма),
 * продавец подтверждает заказ в панели. WhatsApp принимает текст в ссылке; Telegram и ВКонтакте —
 * нет: текст отправляется через «Поделиться» или копируется из блока ниже.
 */
export function AgreementPanel({ order }: { order: OrderDetail }) {
  const s = useStyles();
  const link = order.agreement;
  if (order.status !== "awaiting_agreement") return null;
  if (!link) {
    return (
      <Card style={s.card}>
        <Text style={s.text}>
          Заказ ждёт подтверждения продавца — он свяжется с вами по телефону {order.recipient_phone}.
        </Text>
      </Card>
    );
  }
  const phone = link.kind === "phone";
  return (
    <Card style={s.card}>
      <Text style={s.title}>Согласуйте заказ с продавцом</Text>
      <Text style={s.text}>
        {phone
          ? `Позвоните продавцу и назовите номер заказа ${order.number}.`
          : link.prefilled
            ? "Номер заказа, товары и сумма уже будут в сообщении — просто отправьте его."
            : "Откройте чат и отправьте текст заказа: кнопка «Отправить текст заказа» или скопируйте его ниже."}{" "}
        Товар отложен до {formatDateTime(link.deadline)}: если продавец не подтвердит заказ, он отменится.
      </Text>
      <Button title={BUTTONS[link.kind]} variant="accent" onPress={() => void Linking.openURL(link.url)} />
      {!link.prefilled && !phone ? (
        <Button
          title="Отправить текст заказа"
          variant="secondary"
          onPress={() => void Share.share({ message: link.message }).catch(() => undefined)}
        />
      ) : null}
      <Text style={s.muted}>
        {link.title}: {link.handle}
      </Text>
      {!phone ? (
        <Text style={s.message} selectable>
          {link.message}
        </Text>
      ) : null}
    </Card>
  );
}

const useStyles = makeStyles(({ c }) => ({
  card: { gap: 12, padding: 18 },
  title: { fontFamily: fonts.display700, fontSize: 17, color: c.ink },
  text: { fontFamily: fonts.text600, fontSize: 15, lineHeight: 21, color: c.ink },
  muted: { fontFamily: fonts.text500, fontSize: 13, color: c.muted },
  message: {
    fontFamily: fonts.text500,
    fontSize: 13,
    lineHeight: 19,
    color: c.ink,
    padding: 12,
    borderRadius: radius.control,
    backgroundColor: c.surface,
  },
}));
