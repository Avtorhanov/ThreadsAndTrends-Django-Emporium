import { router } from "expo-router";
import { useEffect, useState } from "react";
import { Text, View } from "react-native";

import { useAuth } from "../../../src/auth/AuthProvider";
import { Icon, type IconName } from "../../../src/components/Icon";
import { Segmented } from "../../../src/components/Segmented";
import { Button, Card, LinkButton, Message, PressScale, Screen, TextField } from "../../../src/components/ui";
import { useSubmit } from "../../../src/hooks/useSubmit";
import { fonts } from "../../../src/theme/fonts";
import { makeStyles, type ThemePreference, useTheme } from "../../../src/theme/ThemeProvider";
import { radius } from "../../../src/theme/tokens";

function ThemeCard() {
  const s = useStyles();
  const { preference, setPreference } = useTheme();
  return (
    <Card style={s.card}>
      <Text style={s.cardTitle}>Оформление</Text>
      <Segmented<ThemePreference>
        label="Тема"
        segments={[
          { value: "system", label: "Как в системе" },
          { value: "light", label: "Светлая" },
          { value: "dark", label: "Тёмная" },
        ]}
        value={preference}
        onChange={setPreference}
      />
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
}));
