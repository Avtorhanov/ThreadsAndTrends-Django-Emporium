import { router, useFocusEffect } from "expo-router";
import { useCallback, useEffect, useState } from "react";
import { Text, View } from "react-native";

import { useAuth } from "../../../src/auth/AuthProvider";
import { Icon, type IconName } from "../../../src/components/Icon";
import { Segmented } from "../../../src/components/Segmented";
import { HelpCard } from "../../../src/content/HelpCard";
import { formatKopecks } from "../../../src/lib/money";
import { formatDateTime, StatusBadge } from "../../../src/orders/components";
import { type OrderSummary, orderService } from "../../../src/orders/orderService";
import { Button, Card, LinkButton, Message, PressScale, Screen, TextField } from "../../../src/components/ui";
import { useSubmit } from "../../../src/hooks/useSubmit";
import { fonts } from "../../../src/theme/fonts";
import { makeStyles, type ThemePreference, useTheme } from "../../../src/theme/ThemeProvider";
import {
  type AccentName,
  accents,
  paletteList,
  paletteThemes,
  radius,
  type RadiusMode,
  type TextMode,
} from "../../../src/theme/tokens";

const RADIUS_SEGMENTS: { value: RadiusMode; label: string }[] = [
  { value: "sharp", label: "Острые" },
  { value: "normal", label: "Средние" },
  { value: "soft", label: "Мягкие" },
];

const TEXT_SEGMENTS: { value: TextMode; label: string }[] = [
  { value: "s", label: "Обычный" },
  { value: "m", label: "Крупнее" },
  { value: "l", label: "Крупный" },
];

/** Оформление: тема, палитра (что разрешил магазин), акцент «Своей», углы, размер текста. */
function ThemeCard() {
  const s = useStyles();
  const { preference, setPreference, look, setLook, palettes, c } = useTheme();
  const available = paletteList.filter((item) => palettes.includes(item.key));
  return (
    <Card style={s.card}>
      <Text style={s.cardTitle}>Оформление</Text>
      <Segmented<ThemePreference>
        label="Тема"
        segments={[
          { value: "system", label: "Системная" },
          { value: "light", label: "Светлая" },
          { value: "dark", label: "Тёмная" },
        ]}
        value={preference}
        onChange={setPreference}
      />
      {available.length > 1 ? (
        <View style={s.lookGroup}>
          <Text style={s.lookLabel}>Палитра</Text>
          <View style={s.swatches} accessibilityRole="radiogroup">
            {available.map((item) => {
              const selected = look.palette === item.key;
              const sample = paletteThemes[item.key].light;
              const dots =
                item.key === "custom"
                  ? (Object.keys(accents) as AccentName[]).slice(0, 4).map((key) => accents[key].color)
                  : [sample.accent, sample.brand, sample.bg];
              return (
                <PressScale
                  key={item.key}
                  accessibilityRole="radio"
                  accessibilityState={{ selected }}
                  accessibilityLabel={`${item.name}. ${item.note}`}
                  onPress={() => setLook({ palette: item.key })}
                  style={[s.swatch, selected && { borderColor: c.ink }]}
                >
                  <View style={s.swatchDots}>
                    {dots.map((color, index) => (
                      <View key={index} style={[s.swatchDot, { backgroundColor: color }]} />
                    ))}
                  </View>
                  <Text style={s.swatchName}>{item.name}</Text>
                </PressScale>
              );
            })}
          </View>
        </View>
      ) : null}
      {look.palette === "custom" ? (
        <View style={s.lookGroup}>
          <Text style={s.lookLabel}>Цвет акцента</Text>
          <View style={s.accents} accessibilityRole="radiogroup">
            {(Object.keys(accents) as AccentName[]).map((key) => {
              const selected = look.accent === key;
              const accent = accents[key];
              return (
                <PressScale
                  key={key}
                  accessibilityRole="radio"
                  accessibilityState={{ selected }}
                  accessibilityLabel={accent.name}
                  onPress={() => setLook({ accent: key })}
                  style={[
                    s.accent,
                    { backgroundColor: accent.color },
                    selected && { borderColor: c.ink, borderWidth: 3 },
                  ]}
                >
                  <Text style={[s.accentText, { color: accent.light.onAccent ?? c.ink }]}>Aa</Text>
                </PressScale>
              );
            })}
          </View>
        </View>
      ) : null}
      <View style={s.lookGroup}>
        <Text style={s.lookLabel}>Углы</Text>
        <Segmented<RadiusMode>
          label="Углы"
          segments={RADIUS_SEGMENTS}
          value={look.radius}
          onChange={(radius) => setLook({ radius })}
        />
      </View>
      <View style={s.lookGroup}>
        <Text style={s.lookLabel}>Размер текста</Text>
        <Segmented<TextMode>
          label="Размер текста"
          segments={TEXT_SEGMENTS}
          value={look.text}
          onChange={(text) => setLook({ text })}
        />
      </View>
    </Card>
  );
}

function MenuRow({ icon, title, onPress }: { icon: IconName; title: string; onPress: () => void }) {
  const s = useStyles();
  const { c } = useTheme();
  return (
    <PressScale accessibilityRole="button" onPress={onPress} scale={0.98} style={s.menuRow}>
      <View style={s.menuIcon}>
        <Icon name={icon} size={20} color={c.tagInk} />
      </View>
      <Text style={s.menuText}>{title}</Text>
      <Icon name="chevron" size={18} color={c.muted} />
    </PressScale>
  );
}

const FINISHED = new Set(["delivered", "cancelled"]);

/** Текущий (незавершённый) заказ — карточка сверху профиля; обновляется при каждом открытии. */
function CurrentOrder() {
  const s = useStyles();
  const [order, setOrder] = useState<OrderSummary | null>(null);

  useFocusEffect(
    useCallback(() => {
      let cancelled = false;
      orderService
        .list(1)
        .then((page) => {
          if (!cancelled) setOrder(page.results.find((item) => !FINISHED.has(item.status)) ?? null);
        })
        .catch(() => undefined); // без сети карточка просто не показывается
      return () => {
        cancelled = true;
      };
    }, []),
  );

  if (!order) return null;
  return (
    <PressScale
      accessibilityRole="button"
      accessibilityLabel={`Текущий заказ ${order.number}, ${order.status_display}`}
      onPress={() => router.push({ pathname: "/orders/[number]", params: { number: order.number } })}
      scale={0.98}
    >
      <Card style={[s.card, s.current]}>
        <Text style={s.caption}>ТЕКУЩИЙ ЗАКАЗ</Text>
        <View style={s.currentTop}>
          <Text style={s.currentNumber}>{order.number}</Text>
          <StatusBadge status={order.status} label={order.status_display} />
        </View>
        <View style={s.currentTop}>
          <Text style={s.muted}>{formatDateTime(order.created_at)}</Text>
          <Text style={s.currentTotal}>{formatKopecks(order.total_kopecks)}</Text>
        </View>
      </Card>
    </PressScale>
  );
}

function GuestProfile() {
  const s = useStyles();
  return (
    <Screen tabs title="Профиль" overline="Аккаунт">
      <Card style={s.card}>
        <Text style={s.lead}>Войдите, чтобы оформлять заказы и следить за их статусом.</Text>
        <Text style={s.muted}>Товары из корзины сохранятся и перенесутся в аккаунт.</Text>
        <Button title="Войти" onPress={() => router.push("/sign-in")} />
        <Button title="Зарегистрироваться" variant="secondary" onPress={() => router.push("/sign-up")} />
      </Card>
      <ThemeCard />
      <HelpCard />
    </Screen>
  );
}

function SignedInProfile() {
  const s = useStyles();
  const { user, updateProfile, logout } = useAuth();
  const [firstName, setFirstName] = useState(user?.first_name ?? "");
  const [lastName, setLastName] = useState(user?.last_name ?? "");
  const [saved, setSaved] = useState(false);

  // Другой пользователь вошёл на этом устройстве — поля формы от него.
  useEffect(() => {
    setFirstName(user?.first_name ?? "");
    setLastName(user?.last_name ?? "");
  }, [user?.id]);

  const save = useSubmit(async () => {
    setSaved(false);
    await updateProfile({ first_name: firstName.trim(), last_name: lastName.trim() });
    setSaved(true);
  });
  const signOut = useSubmit(logout);

  if (!user) return null;
  const name = [user.first_name, user.last_name].filter(Boolean).join(" ");

  return (
    <Screen tabs title={name || "Профиль"} overline="Аккаунт">
      <CurrentOrder />
      <Card style={s.card}>
        <Text style={s.caption}>Email</Text>
        <Text style={s.email}>{user.email}</Text>
        <Text style={s.caption}>С нами с {new Date(user.date_joined).toLocaleDateString("ru-RU")}</Text>
      </Card>

      <Card style={s.menu}>
        <MenuRow icon="box" title="Мои заказы" onPress={() => router.push("/orders")} />
        <View style={s.menuDivider} />
        <MenuRow icon="user" title="Сменить пароль" onPress={() => router.push("/change-password")} />
      </Card>

      <Card style={s.card}>
        <Text style={s.cardTitle}>Личные данные</Text>
        <Message text={save.error} />
        <Message text={saved ? "Изменения сохранены." : null} kind="success" />
        <TextField
          label="Имя"
          value={firstName}
          onChangeText={setFirstName}
          autoComplete="given-name"
          errors={save.fieldErrors.first_name}
        />
        <TextField
          label="Фамилия"
          value={lastName}
          onChangeText={setLastName}
          autoComplete="family-name"
          errors={save.fieldErrors.last_name}
        />
        <Button title="Сохранить" variant="secondary" onPress={() => void save.submit()} loading={save.loading} />
      </Card>

      <ThemeCard />

      <HelpCard />

      <Button title="Выйти" variant="secondary" onPress={() => void signOut.submit()} loading={signOut.loading} />
      <LinkButton title="Удалить аккаунт" tone="danger" onPress={() => router.push("/delete-account")} />
    </Screen>
  );
}

/** Вкладка «Профиль»: гостю — вход и регистрация, клиенту — аккаунт и заказы. Тема — всем. */
export default function ProfileScreen() {
  const { status } = useAuth();
  return status === "signedIn" ? <SignedInProfile /> : <GuestProfile />;
}

const useStyles = makeStyles(({ c }) => ({
  card: { gap: 12, padding: 18 },
  lookGroup: { gap: 8 },
  lookLabel: { fontFamily: fonts.text700, fontSize: 12, letterSpacing: 0.8, color: c.muted, textTransform: "uppercase" },
  swatches: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  swatch: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    minHeight: 48,
    paddingHorizontal: 12,
    borderRadius: radius.control,
    borderWidth: 2,
    borderColor: "transparent",
    backgroundColor: c.surface,
  },
  swatchDots: { flexDirection: "row", gap: 3 },
  swatchDot: { width: 14, height: 14, borderRadius: 5, borderWidth: 1, borderColor: "rgba(0,0,0,0.12)" },
  swatchName: { fontFamily: fonts.text700, fontSize: 14, color: c.ink },
  accents: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  accent: {
    width: 48,
    height: 48,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: radius.seg,
    borderWidth: 1,
    borderColor: "rgba(0,0,0,0.12)",
  },
  accentText: { fontFamily: fonts.text700, fontSize: 14 },
  cardTitle: { fontFamily: fonts.display700, fontSize: 17, color: c.ink },
  lead: { fontFamily: fonts.text700, fontSize: 16, lineHeight: 22, color: c.ink },
  muted: { fontFamily: fonts.text500, fontSize: 14, lineHeight: 20, color: c.muted },
  caption: { fontFamily: fonts.text700, fontSize: 13, color: c.muted },
  email: { fontFamily: fonts.text800, fontSize: 18, color: c.ink },
  menu: { paddingVertical: 6, paddingHorizontal: 8 },
  menuRow: { minHeight: 56, flexDirection: "row", alignItems: "center", gap: 12, paddingHorizontal: 8 },
  menuIcon: {
    width: 38,
    height: 38,
    borderRadius: radius.control - 3,
    backgroundColor: c.tag,
    alignItems: "center",
    justifyContent: "center",
  },
  menuText: { flex: 1, fontFamily: fonts.text700, fontSize: 16, color: c.ink },
  menuDivider: { height: 1, marginHorizontal: 8, backgroundColor: c.border },
  current: { borderWidth: 1.5, borderColor: c.brand },
  currentTop: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: 10 },
  currentNumber: { fontFamily: fonts.display700, fontSize: 18, color: c.ink },
  currentTotal: { fontFamily: fonts.display700, fontSize: 17, color: c.ink },
}));
