from loader import bot, app_logger
import handlers  # noqa
from telebot.custom_filters import StateFilter
from utils.set_bot_commands import set_default_commands
from database.models import create_models
from config_data.config import ADMIN_ID
from apscheduler.schedulers.background import BackgroundScheduler

from utils.tasks import check_and_revoke_keys

if __name__ == '__main__':
    create_models()
    app_logger.debug("Подключение к базе данных...")
    bot.add_custom_filter(StateFilter(bot))
    set_default_commands(bot)
    app_logger.info("Загрузка базовых команд...")

    scheduler = BackgroundScheduler()
    # Запуск проверки каждые 5 минут
    scheduler.add_job(check_and_revoke_keys, 'interval', minutes=5)
    scheduler.start()
    app_logger.info("Запущен планировщик для проверки подписки пользователей и отзыва ключей.")

    app_logger.info(f"Бот @{bot.get_me().username} запущен.")
    bot.send_message(ADMIN_ID, "Бот запущен.")
    bot.infinity_polling()
