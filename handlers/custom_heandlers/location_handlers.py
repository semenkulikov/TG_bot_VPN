from telebot.types import Message

from config_data.config import ALLOWED_USERS
from database.models import User
from keyboards.inline.accounts import users_markup
from loader import bot, app_logger
from states.states import AdminPanel


@bot.message_handler(commands=["location"])
def location_handler(message: Message):
    """ Хендлер для выбора сервера подключения """
    cur_user = User.get(User.user_id == message.from_user.id)

    if cur_user.is_subscribed:
        bot.send_message(message.chat.id, "Выберите сервер подключения:")
    else:
        bot.send_message(message.chat.id, "Вы не подписаны на канал!")
