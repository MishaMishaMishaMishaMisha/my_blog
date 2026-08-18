import logging
from pathlib import Path
import os

from source.core.config import settings


class SimpleLoggerFactory:
    DEFAULT_FMT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    DEFAULT_DATEFMT = "%d.%m.%y %H:%M:%S"

    def __init__(
        self,
        name: str | None = None,
        level: int = logging.DEBUG,
        handler: logging.Handler | None = None,
        formatter: logging.Formatter | None = None,
        fmt: str | None = None,
        log_filter: logging.Filter | None = None,
    ):
        
        self.logger = logging.getLogger(name)
        
        self.logger.setLevel(level)
        
        if handler is None:
            handler = logging.StreamHandler()

        if formatter is None:
            formatter = logging.Formatter(fmt or self.DEFAULT_FMT, datefmt=self.DEFAULT_DATEFMT)
            
        handler.setFormatter(formatter)
            
        if log_filter is not None:
            handler.addFilter(log_filter)

        self.logger.addHandler(handler)
        
        self.formatter = formatter
        self.filter = log_filter

    def add_handler(self, handler: logging.Handler) -> None:
        handler.setFormatter(self.formatter)
        
        if self.filter is not None:
            handler.addFilter(self.filter)
        
        self.logger.addHandler(handler)

    def add_formatter(self, formatter: logging.Formatter, handler: logging.Handler | None = None) -> None:
        if handler:
            handler.setFormatter(formatter)
        else:
            for h in self.logger.handlers:
                h.setFormatter(formatter)

    def set_format(self, fmt: str, datefmt: str = DEFAULT_DATEFMT) -> None:
        formatter = logging.Formatter(fmt, datefmt=datefmt)
        self.add_formatter(formatter)

    def add_filter(self, log_filter: logging.Filter) -> None:
        for handler in self.logger.handlers:
            handler.addFilter(log_filter)

    def get_logger(self) -> logging.Logger:
        return self.logger
    
    
if os.getenv("MODE") == "TEST":
    # файл с логами из тестов будет лежать в папке tests/
    BASE_DIR = Path(__file__).resolve().parent.parent.parent
    logs_path = BASE_DIR / "tests/test_logs.log"

else:
    # файл с логами будет лежать в отдельной папке
    BASE_DIR = Path(__file__).resolve().parent.parent.parent
    logs_path = BASE_DIR / "logs/logs.log"

filehandler = logging.FileHandler(logs_path)

log_level = settings.LOG_LEVEL
if log_level not in logging.getLevelNamesMapping():
    log_leve = "DEBUG"
    
print("app executed with log-level=", log_level)

loggger_factory = SimpleLoggerFactory(name="default-logger", 
                                      level=logging._nameToLevel[log_level])
loggger_factory.add_handler(filehandler)

# логгер по умолчанию уровень DEBUG, вывод в консоль и в файл
default_logger = loggger_factory.get_logger()



