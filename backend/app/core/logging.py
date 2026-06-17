import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any
from app.core.config import settings


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        if hasattr(record, "extra"):
            log_entry.update(record.extra)
        if record.exc_info and record.exc_info[0]:
            log_entry["exception"] = self.formatException(record.exc_info)
        if record.stack_info:
            log_entry["stack_info"] = self.formatStack(record.stack_info)
        return json.dumps(log_entry)


def setup_logging():
    logger = logging.getLogger("prometheus")
    logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))

    handler = logging.StreamHandler(sys.stdout)
    if settings.LOG_FORMAT == "json":
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
    logger.addHandler(handler)

    if settings.LOG_FILE:
        file_handler = logging.FileHandler(settings.LOG_FILE)
        file_handler.setFormatter(JSONFormatter())
        logger.addHandler(file_handler)

    return logger


logger = setup_logging()
