from telebot.types import Message
from database.models import User
from loader import bot, app_logger
from keyboards.inline.app_buttons import get_apps_murkup


@bot.message_handler(commands=["instruction"])
def instruction_handler(message: Message):
    """ Хендлер для выбора сервера подключения """
    app_logger.info(f"Пользователь {message.from_user.full_name} вызвал команду /location")
    cur_user = User.get(User.user_id == message.from_user.id)

    if cur_user.is_subscribed:
        instruction_text = """Все инструкции для подключения располагаются по [ссылке](https://telegra.ph/Kak-ispolzovat-VPN-servis-Guard-Tunnel-01-16)
Для использования VPN вам необходимо скачать приложение Hiddify
"""
        bot.send_message(message.chat.id, instruction_text, parse_mode="Markdown", reply_markup=get_apps_murkup())
    else:
        bot.send_message(message.chat.id, "Вы не подписаны на канал!")
