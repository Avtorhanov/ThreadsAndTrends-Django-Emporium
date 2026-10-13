from django.dispatch import Signal

# Отправляется после мягкого удаления пользователя (sender=User, user=<User>).
# Приложения чистят свои данные (например, корзину), не создавая зависимость accounts → app.
account_deleted = Signal()
