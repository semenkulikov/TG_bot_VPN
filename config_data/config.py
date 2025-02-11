import os
from dotenv import load_dotenv, find_dotenv

if not find_dotenv():
    exit('Переменные окружения не загружены, т.к отсутствует файл .env')
else:
    load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
DEFAULT_COMMANDS = (
    ('start', "Запустить бота"),
    ('help', "Вывести справку"),
    ('location', "Выбрать сервера для подключения"),
    ('instruction', "Запросить инструкцию для подключения VPN"),
)
ADMIN_COMMANDS = (
    ("admin_panel", "Админка"),
    ("message_sending", "Рассылка сообщений"),
    ("add_vpn_key", "Вручную добавить VPN ключ")
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH_TO_PYTHON = os.path.normpath(os.path.join(BASE_DIR, ".venv/bin/python.exe"))
ADMIN_ID = os.getenv('ADMIN_ID')
ALLOWED_USERS = [int(ADMIN_ID),
                 418333240,  # владелец канала
                 ]

CHANNEL_ID = os.getenv('CHANNEL_ID')

DEFAULT_SERVER_USER = os.getenv("DEFAULT_SERVER_USER")
DEFAULT_SERVER_PASSWORD = os.getenv("DEFAULT_SERVER_PASSWORD")
