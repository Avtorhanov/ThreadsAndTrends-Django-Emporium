import { type ReactNode, createContext, useContext } from "react";

const ViewOnlyContext = createContext(false);

export const ViewOnlyProvider = ViewOnlyContext.Provider;

/** Сотрудник с правом «Смотреть» на текущий раздел. Запрет проверяет сервер, здесь — вид экрана. */
export function useViewOnly(): boolean {
  return useContext(ViewOnlyContext);
}

/** Блок с действиями: в режиме просмотра браузер отключает всё внутри (кнопки, поля, загрузку). */
export function Editable({ children }: { children: ReactNode }) {
  const viewOnly = useViewOnly();
  return (
    <fieldset className="editable" disabled={viewOnly}>
      {children}
    </fieldset>
  );
}
