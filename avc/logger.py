import logging
import os
from logging.handlers import TimedRotatingFileHandler
from typing import override


class CustomFormatter(logging.Formatter):
    @override
    def format(self, record: logging.LogRecord) -> str:
        level = record.levelname
        level = level if level != "WARNING" else "WARN"
        level = f"{level:>5}"
        location = f"{record.filename}:{record.lineno}"
        time = self.formatTime(record, "%H:%M:%S")
        msg = record.getMessage()
        return f"[{time}] {level} {location:<18} {msg}"


def get_logger(name: str) -> logging.Logger:
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f"{name}.log")

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    if not logger.handlers:
        log_fmt = CustomFormatter(
            "[%(asctime)s] %(levelname)-5s %(filename)s:%(lineno)s %(message)s",
            datefmt="%H:%M:%S",
        )

        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(log_fmt)

        file_handler = TimedRotatingFileHandler(
            log_file, when="h", interval=12, backupCount=0, encoding="utf-8"
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(log_fmt)

        logger.addHandler(console_handler)
        logger.addHandler(file_handler)

    return logger
