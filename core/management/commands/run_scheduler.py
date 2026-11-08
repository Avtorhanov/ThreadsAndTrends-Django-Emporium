import logging
import signal
import time

from django.core.management.base import BaseCommand

from core.monitoring import check_and_alert
from core.periodic import enqueue_due, load_periodic_tasks

logger = logging.getLogger(__name__)
MONITOR_EVERY = 10 * 60


class Command(BaseCommand):
    help = "Ставит в очередь периодические задачи из settings.PERIODIC_TASKS."

    def add_arguments(self, parser):
        parser.add_argument("--tick", type=int, default=15, help="Период проверки, секунд")
        parser.add_argument("--once", action="store_true", help="Одна проверка и выход")

    def handle(self, *args, tick: int, once: bool, **options):
        tasks = load_periodic_tasks()
        self.stdout.write(f"Планировщик: задач {len(tasks)}, проверка каждые {tick} с")

        self._running = True
        checked_at = time.monotonic()  # сразу после старта службы ещё не успели поработать
        signal.signal(signal.SIGTERM, self._stop)
        signal.signal(signal.SIGINT, self._stop)

        while self._running:
            enqueue_due(tasks)
            if once:
                break
            if time.monotonic() - checked_at >= MONITOR_EVERY:
                checked_at = time.monotonic()
                try:
                    check_and_alert()
                except Exception:  # сбой проверки не должен останавливать планировщик
                    logger.exception("Мониторинг: проверка не выполнена")
            # Спим по секунде, чтобы SIGTERM от Docker обрабатывался без ожидания tick.
            for _ in range(tick):
                if not self._running:
                    break
                time.sleep(1)

    def _stop(self, signum, frame):
        self._running = False
