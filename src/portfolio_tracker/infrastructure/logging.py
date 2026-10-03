import logging
from logging.handlers import TimedRotatingFileHandler

from .configuration import Configuration


def configure_desktop_cli_logging(configuration: Configuration) -> None:
    handler = TimedRotatingFileHandler(
        configuration.log_dir / "portfolio_tracker.log",
        when="midnight",
        backupCount=30,
    )
    handler.setFormatter(
        logging.Formatter("%(asctime)s | %(levelname)-8s | %(name)s | %(message)s")
    )
    app_logger = logging.getLogger("portfolio_tracker")
    app_logger.addHandler(handler)
    app_logger.setLevel(logging.DEBUG if configuration.debug else logging.INFO)
