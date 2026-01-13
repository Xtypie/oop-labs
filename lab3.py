from abc import ABC, abstractmethod
from enum import Enum
import re
import socket
from ftplib import FTP
import os
import tempfile
from datetime import datetime


class LogLevel(Enum):
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"


class ILogFilter(ABC):
    @abstractmethod
    def match(self, log_level: LogLevel, text: str) -> bool:
        ...


class SimpleLogFilter(ILogFilter):
    def __init__(self, pattern: str) -> None:
        self.pattern = pattern

    def match(self, log_level: LogLevel, text: str) -> bool:
        return self.pattern in text


class ReLogFilter(ILogFilter):
    def __init__(self, pattern: str) -> None:
        self.pattern = pattern

    def match(self, log_level: LogLevel, text: str) -> bool:
        try:
            return re.fullmatch(self.pattern, text) is not None
        except Exception:
            return False


class LevelFilter(ILogFilter):
    def __init__(self, log_level: LogLevel) -> None:
        self.log_level = log_level

    def match(self, log_level: LogLevel, text: str) -> bool:
        return self.log_level == log_level


class ILogHandler(ABC):
    @abstractmethod
    def handle(self, log_level: LogLevel, text: str) -> None:
        ...


class ConsoleHandler(ILogHandler):
    def handle(self, log_level: LogLevel, text: str) -> None:
        print(text)


class FileHandler(ILogHandler):
    def __init__(self, file_path: str) -> None:
        self.file_path = file_path

    def handle(self, log_level: LogLevel, text: str) -> None:
        try:
            with open(self.file_path, "a", encoding="utf-8") as file:
                file.write(f"{text}\n")
        except Exception:
            pass


class SocketHandler(ILogHandler):
    def __init__(self, host: str, port: int) -> None:
        self.host = host
        self.port = port

    def handle(self, log_level: LogLevel, text: str) -> None:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client:
                client.connect((self.host, self.port))
                client.sendall(text.encode('utf-8'))
        except Exception:
            pass


class SyslogHandler(ILogHandler):
    def __init__(self, log_dir: str = "/var/log/myapp", app_name: str = "app") -> None:
        self.log_dir = log_dir
        self.app_name = app_name
        os.makedirs(log_dir, exist_ok=True)
        self.log_file = os.path.join(log_dir, f"{app_name}.log")

    def handle(self, log_level: LogLevel, text: str) -> None:
        try:
            with open(self.log_file, "a", encoding="utf-8") as file:
                file.write(text)
        except Exception:
            pass


class FtpHandler(ILogHandler):
    def __init__(self, host: str, username: str, password: str) -> None:
        self.host = host
        self.username = username
        self.password = password

    def handle(self, log_level: LogLevel, text: str) -> None:
        try:
            with tempfile.NamedTemporaryFile("w+", encoding="utf-8", delete=False) as tmp:
                tmp.write(text)
                tmp.flush()
                tmp_name = tmp.name

            ftp = FTP(self.host)
            ftp.login(self.username, self.password)
            ftp.cwd("/logs")

            with open(tmp_name, "rb") as f:
                ftp.storbinary(f"STOR log_{os.path.basename(tmp_name)}.txt", f)

            ftp.quit()
            os.remove(tmp_name)
        except Exception:
            pass


class ILogFormatter(ABC):
    @abstractmethod
    def format(self, log_level: LogLevel, text: str) -> str:
        ...


class LevelAndTimeFormatter(ILogFormatter):
    def __init__(self, data: str = "%Y.%m.%d %H:%M:%S"):
        self.data = data

    def format(self, log_level: LogLevel, text: str) -> str:
        now = datetime.now()
        data_str = now.strftime(self.data)
        return f'[{log_level}] [{data_str}] {text}'


class Logger:
    def __init__(self, log_filters: list[ILogFilter], log_handlers: list[ILogHandler],
                 log_formatters: list[ILogFormatter]):
        self.log_filters = log_filters
        self.log_handlers = log_handlers
        self.log_formatters = log_formatters

    def log(self, log_level: LogLevel, text: str) -> None:
        if not all(filter.match(log_level, text) for filter in self.log_filters):
            return

        for formatter in self.log_formatters:
            text = formatter.format(log_level, text)

        for handler in self.log_handlers:
            handler.handle(log_level=log_level, text=text)

    def log_info(self, text: str) -> None:
        self.log(LogLevel.INFO, text)

    def log_warn(self, text: str) -> None:
        self.log(LogLevel.WARN, text)

    def log_error(self, text: str) -> None:
        self.log(LogLevel.ERROR, text)

    def add_log_filter(self, log_filter: ILogFilter) -> None:
        self.log_filters.append(log_filter)

    def add_log_formatter(self, log_formatter: ILogFormatter) -> None:
        self.log_formatters.append(log_formatter)

    def add_log_handler(self, log_handler: ILogHandler) -> None:
        self.log_handlers.append(log_handler)

    def remove_log_filter(self, log_filter: ILogFilter) -> None:
        self.log_filters.remove(log_filter)

    def remove_log_formatter(self, log_formatter: ILogFormatter) -> None:
        self.log_formatters.remove(log_formatter)

    def remove_log_handler(self, log_handler: ILogHandler) -> None:
        self.log_handlers.remove(log_handler)


if __name__ == "__main__":
    filters = [
        LevelFilter(LogLevel.WARN),
        SimpleLogFilter("disk"),
        ReLogFilter(r".*full.*")
    ]

    handlers = [
        ConsoleHandler(),
        FileHandler("log_demo_extended.txt")
    ]

    formatter = [LevelAndTimeFormatter("%d/%m/%Y %I:%M %p")] # здесь меняется формат вывода даты

    logger = Logger(filters, handlers, formatter)

    test_messages = [
        (LogLevel.INFO, "disk space ok"),
        (LogLevel.WARN, "disk almost full"),
        (LogLevel.WARN, "disk usage high"),
        (LogLevel.WARN, "memory full"),
        (LogLevel.ERROR, "disk almost full"),
        (LogLevel.WARN, "disk full backup"),
    ]

    for level, msg in test_messages:
        logger.log(level, msg)
