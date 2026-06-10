import logging
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

# Project root / logs/
LOG_DIR = Path(__file__).parents[3] / "logs"

_FORMAT = "%(asctime)s | %(levelname)-8s | %(message)s"
_DATE_FMT = "%Y-%m-%d %H:%M:%S"


def _file_handler(filename: str, level: int = logging.DEBUG) -> TimedRotatingFileHandler:
    LOG_DIR.mkdir(exist_ok=True)
    handler = TimedRotatingFileHandler(
        filename=LOG_DIR / filename,
        when="midnight",
        backupCount=30,
        encoding="utf-8"
    )
    handler.suffix = "%Y-%m-%d"
    handler.setLevel(level)
    handler.setFormatter(logging.Formatter(_FORMAT, datefmt=_DATE_FMT))
    return handler


def setup_logging() -> None:
    formatter = logging.Formatter(_FORMAT, datefmt=_DATE_FMT)

    # application — business events
    _configure("app.application", logging.INFO, _file_handler("application.log"))

    # rag — retrieval details
    _configure("app.rag", logging.INFO, _file_handler("rag.log"))

    # openai — API usage and cost tracking
    _configure("app.openai", logging.INFO, _file_handler("openai.log"))

    # errors — exceptions with full tracebacks
    _configure("app.errors", logging.ERROR, _file_handler("errors.log", level=logging.ERROR))

    # root logger → console (development convenience)
    root = logging.getLogger()
    if not root.handlers:
        console = logging.StreamHandler()
        console.setLevel(logging.INFO)
        console.setFormatter(formatter)
        root.addHandler(console)
    root.setLevel(logging.INFO)


def _configure(name: str, level: int, handler: logging.Handler) -> None:
    logger = logging.getLogger(name)
    logger.setLevel(level)
    if not logger.handlers:
        logger.addHandler(handler)
    logger.propagate = False
