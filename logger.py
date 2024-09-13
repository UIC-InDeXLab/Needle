import logging
from logging.handlers import TimedRotatingFileHandler
import os

# Create logs directory if it doesn't exist
if not os.path.exists('logs'):
    os.makedirs('logs')

# Configure logger
logger = logging.getLogger("Needle Logger")
logger.setLevel(logging.INFO)

# Create handlers
console_handler = logging.StreamHandler()  # Log to console
file_handler = TimedRotatingFileHandler('logs/app.log', when="midnight", interval=1)  # Log to file, rotated at midnight
file_handler.suffix = "%Y%m%d"

# Create formatter and add it to the handlers
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
file_handler.setFormatter(formatter)

# Add handlers to the logger
logger.addHandler(console_handler)
logger.addHandler(file_handler)
