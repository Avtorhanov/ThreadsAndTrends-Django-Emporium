import { useCallback, useRef, useState } from "react";

import { ApiError, type FieldErrors } from "../api/errors";

/** Состояние отправки формы: загрузка, общая ошибка и ошибки полей из ответа API. */
export function useSubmit<Args extends unknown[]>(action: (...args: Args) => Promise<void>) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});
  const inFlight = useRef(false);

  const submit = useCallback(
    async (...args: Args): Promise<boolean> => {
      if (inFlight.current) return false; // защита от двойного нажатия
      inFlight.current = true;
      setLoading(true);
      setError(null);
      setFieldErrors({});
      try {
        await action(...args);
        return true;
      } catch (err) {
        if (err instanceof ApiError) {
          setError(err.message);
          setFieldErrors(err.fieldErrors);
        } else {
          setError("Что-то пошло не так. Попробуйте ещё раз.");
        }
        return false;
      } finally {
        inFlight.current = false;
        setLoading(false);
      }
    },
    [action],
  );

  return { submit, loading, error, fieldErrors };
}
