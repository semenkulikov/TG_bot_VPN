import os.path

from apscheduler.schedulers.background import BackgroundScheduler
from telebot import TeleBot
from telebot.storage import StateMemoryStorage
from config_data import config
from logging.handlers import RotatingFileHandler
import logging

from config_data.config import BASE_DIR

storage = StateMemoryStorage()
bot = TeleBot(token=config.BOT_TOKEN, state_storage=storage)
scheduler = BackgroundScheduler()


log_formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(name)s - %(message)s')
my_handler = RotatingFileHandler(os.path.join(BASE_DIR, "bot.log"), mode='a', maxBytes=5 * 1024 * 1024,
                                 backupCount=1, encoding="utf8", delay=0)
my_handler.setFormatter(log_formatter)
my_handler.setLevel(logging.DEBUG)

stream_handler = logging.StreamHandler()
stream_handler.setFormatter(log_formatter)
stream_handler.setLevel(logging.INFO)

app_logger = logging.getLogger("app_logger")
app_logger.setLevel(logging.DEBUG)
app_logger.addHandler(my_handler)
app_logger.addHandler(stream_handler)
