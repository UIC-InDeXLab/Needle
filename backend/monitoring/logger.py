# monitoring/logger.py
import logging
import os
from datetime import datetime


class NeedleLogger:
    def __init__(self):
        self._logger = self._setup_logger()

    @staticmethod
    def _resolve_log_dir():
        # Write logs to a writable per-user location, never the (possibly
        # read-only) install/working directory.
        base = os.environ.get("NEEDLE_DATA_DIR")
        if not base:
            base = os.path.join(os.path.expanduser("~"), ".needle", "data")
        return os.path.join(base, "logs")

    def _setup_logger(self):
        logger_name = "Needle Logger"
        logger = logging.getLogger(logger_name)
        if logger.handlers:
            return logger

        logger.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(filename)s - %(levelname)s - %(message)s')

        # Console logging always works.
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # File logging is best-effort; skip it if the directory isn't writable.
        try:
            log_directory = self._resolve_log_dir()
            os.makedirs(log_directory, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_filename = os.path.join(log_directory, f"app_{timestamp}.log")
            file_handler = logging.FileHandler(log_filename)
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except OSError:
            pass

        return logger

    def __getattr__(self, name):
        # Get the attribute from the underlying logger.
        attr = getattr(self._logger, name)
        # If it is a logging method, wrap it to pass a default stacklevel.
        if callable(attr) and name in ('debug', 'info', 'warning', 'error', 'critical', 'exception'):
            def wrapped(*args, **kwargs):
                # Set stacklevel=3 by default so that the caller’s file is recorded
                if 'stacklevel' not in kwargs:
                    kwargs['stacklevel'] = 3
                return attr(*args, **kwargs)

            return wrapped
        return attr


# Create a global logger instance.
logger = NeedleLogger()
