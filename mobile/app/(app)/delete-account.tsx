import { useState } from "react";
import { Alert } from "react-native";

import { useAuth } from "../../src/auth/AuthProvider";
import { Button, Hint, Message, Screen, TextField } from "../../src/components/ui";
import { useSubmit } from "../../src/hooks/useSubmit";

export default function DeleteAccountScreen() {
  const { deleteAccount } = useAuth();
  const [password, setPassword] = useState("");
  const { submit, loading, error, fieldErrors } = useSubmit(() => deleteAccount(password));

  const confirm = () =>
    Alert.alert("Удалить аккаунт?", "Действие необратимо.", [
      { text: "Отмена", style: "cancel" },
      { text: "Удалить", style: "destructive", onPress: () => void submit() },
    ]);

  return (
    <Screen>
      <Hint>
        Профиль будет удалён, имя и email обезличены, вход станет невозможен. История заказов
        сохраняется в обезличенном виде — этого требует бухгалтерский учёт.
      </Hint>
      <Message text={error} />
      <TextField
        label="Пароль для подтверждения"
        value={password}
        onChangeText={setPassword}
        secureTextEntry
        autoComplete="current-password"
        textContentType="password"
        errors={fieldErrors.password}
      />
      <Button
        title="Удалить аккаунт"
        variant="danger"
        onPress={confirm}
        loading={loading}
        disabled={!password}
      />
    </Screen>
  );
}
