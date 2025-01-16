from telebot.types import Message
from database.models import User
from loader import bot, app_logger


@bot.message_handler(commands=["location"])
def location_handler(message: Message):
    """ Хендлер для выбора сервера подключения """
    app_logger.info(f"Пользователь {message.from_user.full_name} вызвал команду /location")
    cur_user = User.get(User.user_id == message.from_user.id)

    if cur_user.is_subscribed:
        bot.send_message(message.chat.id, "Выберите сервер подключения:")
    else:
        bot.send_message(message.chat.id, "Вы не подписаны на канал!")
