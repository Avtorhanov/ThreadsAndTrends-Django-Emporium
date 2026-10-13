from django.dispatch import Signal

# Перед мягким удалением (sender=User, user=<User>). Приёмник может запретить удаление,
# бросив django.core.exceptions.ValidationError (например, есть незавершённые заказы).
account_deleting = Signal()

# После мягкого удаления. Приложения обезличивают и чистят свои данные (корзина, заказы),
# не создавая зависимость accounts → app.
account_deleted = Signal()
