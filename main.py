from loader import bot, app_logger
import handlers  # noqa
from telebot.custom_filters import StateFilter
from utils.set_bot_commands import set_default_commands
from database.models import create_models
from config_data.config import ADMIN_ID

if __name__ == '__main__':
    create_models()
    app_logger.debug("Подключение к базе данных...")
    bot.add_custom_filter(StateFilter(bot))
    set_default_commands(bot)
    app_logger.info("Загрузка базовых команд...")
    app_logger.info("Бот запущен.")
    bot.send_message(ADMIN_ID, "Бот запущен.")
    bot.infinity_polling()
