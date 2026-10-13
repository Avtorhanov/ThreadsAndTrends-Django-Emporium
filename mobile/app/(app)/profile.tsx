import { router } from "expo-router";
import { useState } from "react";
import { StyleSheet, Text, View } from "react-native";

import { useAuth } from "../../src/auth/AuthProvider";
import { colors, radius, spacing } from "../../src/components/theme";
import { Button, LinkButton, Message, Screen, TextField } from "../../src/components/ui";
import { useSubmit } from "../../src/hooks/useSubmit";

export default function ProfileScreen() {
  const { user, updateProfile, logout } = useAuth();
  const [firstName, setFirstName] = useState(user?.first_name ?? "");
  const [lastName, setLastName] = useState(user?.last_name ?? "");
  const [saved, setSaved] = useState(false);

  const save = useSubmit(async () => {
    setSaved(false);
    await updateProfile({ first_name: firstName.trim(), last_name: lastName.trim() });
    setSaved(true);
  });
  const signOut = useSubmit(logout);

  if (!user) return null;

  return (
    <Screen>
      <View style={styles.card}>
        <Text style={styles.caption}>Email</Text>
        <Text style={styles.email}>{user.email}</Text>
        <Text style={styles.caption}>
          С нами с {new Date(user.date_joined).toLocaleDateString("ru-RU")}
        </Text>
      </View>

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
      <Button title="Сохранить" onPress={() => void save.submit()} loading={save.loading} />

      <LinkButton title="Сменить пароль" onPress={() => router.push("/change-password")} />
      <Button
        title="Выйти"
        variant="secondary"
        onPress={() => void signOut.submit()}
        loading={signOut.loading}
      />
      <LinkButton title="Удалить аккаунт" onPress={() => router.push("/delete-account")} />
    </Screen>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.surface,
    borderRadius: radius,
    padding: spacing.md,
    gap: spacing.xs,
    borderWidth: 1,
    borderColor: colors.border,
  },
  caption: { color: colors.muted, fontSize: 13 },
  email: { color: colors.text, fontSize: 18, fontWeight: "600" },
});
