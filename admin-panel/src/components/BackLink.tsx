import { useLocation, useNavigate } from "react-router";

import { Icon } from "./Icon";

/**
 * «‹ Назад» — в строке заголовка, только на вложенных экранах (товар, заказ, статья, черновики,
 * пачка); у разделов из меню кнопки нет. Шаг назад по истории панели — возвращает прокрутку и
 * фильтры списка; открыли экран по прямой ссылке — в родительский раздел `to`.
 */
export function BackLink({ to }: { to: string }) {
  const navigate = useNavigate();
  const location = useLocation();
  return (
    <button
      type="button"
      className="page-back"
      onClick={() => {
        // "default" — первая страница сессии: истории внутри панели нет.
        if (location.key !== "default" && window.history.length > 1) void navigate(-1);
        else void navigate(to);
      }}
    >
      <Icon name="left" size={16} />
      Назад
    </button>
  );
}
