import logging
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

from .configuration import Configuration


def configure_logging(configuration: Configuration) -> Path:
    log_file = configuration.log_dir / "portfolio_tracker.log"
    handler = TimedRotatingFileHandler(
        log_file,
        when="midnight",
        backupCount=30,
    )
    handler.setFormatter(
        logging.Formatter("%(asctime)s | %(levelname)-8s | %(name)s | %(message)s")
    )
    app_logger = logging.getLogger("portfolio_tracker")
    app_logger.addHandler(handler)
    app_logger.setLevel(logging.DEBUG if configuration.debug else logging.INFO)
    return log_file
