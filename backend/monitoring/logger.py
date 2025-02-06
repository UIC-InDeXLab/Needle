# monitoring/logger.py
import logging
import os
from datetime import datetime


class NeedleLogger:
    def __init__(self):
        self._logger = self._setup_logger()

    def _setup_logger(self):
        log_directory = 'logs'
        os.makedirs(log_directory, exist_ok=True)

        # Use a fixed logger name for the entire application
        logger_name = "Needle Logger"
        # Create one log file per app run using a timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_filename = os.path.join(log_directory, f"app_{timestamp}.log")

        logger = logging.getLogger(logger_name)
        if not logger.handlers:
            logger.setLevel(logging.INFO)

            file_handler = logging.FileHandler(log_filename)
            file_handler.setLevel(logging.INFO)

            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)

            # Include the caller's filename in each log record via %(filename)s
            formatter = logging.Formatter('%(asctime)s - %(filename)s - %(levelname)s - %(message)s')
            file_handler.setFormatter(formatter)
            console_handler.setFormatter(formatter)

            logger.addHandler(file_handler)
            logger.addHandler(console_handler)
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
