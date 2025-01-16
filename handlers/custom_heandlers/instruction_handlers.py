from telebot.types import Message
from database.models import User
from loader import bot, app_logger


@bot.message_handler(commands=["instruction"])
def instruction_handler(message: Message):
    """ Хендлер для выбора сервера подключения """
    app_logger.info(f"Пользователь {message.from_user.full_name} вызвал команду /location")
    cur_user = User.get(User.user_id == message.from_user.id)

    if cur_user.is_subscribed:
        instruction_text = """Все инструкции для подключения располагаются по [ссылке](https://telegra.ph/Kak-ispolzovat-VPN-servis-Guard-Tunnel-01-16)
Вам необходимо скачать приложение [Hiddify](https://github.com/hiddify/hiddify-app/releases)
"""
        bot.send_message(message.chat.id, instruction_text, parse_mode="Markdown")
    else:
        bot.send_message(message.chat.id, "Вы не подписаны на канал!")
