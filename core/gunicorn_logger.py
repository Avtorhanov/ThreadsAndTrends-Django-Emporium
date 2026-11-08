"""Журнал gunicorn без секрета гостевой ссылки на заказ."""

import re

from gunicorn.glogging import Logger

_GUEST_LINK = re.compile(r"/order/g/[^/ ?]+")


class MaskingLogger(Logger):
    def atoms(self, resp, req, environ, request_time):
        atoms = super().atoms(resp, req, environ, request_time)
        for name in ("r", "U"):
            atoms[name] = _GUEST_LINK.sub("/order/g/***", atoms[name])
        return atoms
