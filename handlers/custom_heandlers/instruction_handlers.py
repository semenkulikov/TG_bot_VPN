from telebot.types import Message

from config_data.config import CHANNEL_ID
from database.models import User
from loader import bot, app_logger
from keyboards.inline.app_buttons import get_apps_murkup


@bot.message_handler(commands=["instruction"])
def instruction_handler(message: Message):
    """ Хендлер для выбора сервера подключения """
    app_logger.info(f"Пользователь {message.from_user.full_name} вызвал команду /location")
    cur_user = User.get(User.user_id == message.from_user.id)

    if cur_user.is_subscribed:
        instruction_text = (
            "📖 Подробная инструкция по подключению доступна по [ссылке]"
            "(https://telegra.ph/Kak-ispolzovat-VPN-servis-Guard-Tunnel-01-16).\n\n"
            "💡 Для использования VPN, пожалуйста, скачайте приложение **Hiddify**.\n\n"
            "Желаем вам безопасного и комфортного подключения! 🚀"
        )
        bot.send_message(message.chat.id, instruction_text, parse_mode="Markdown", reply_markup=get_apps_murkup())
    else:
        bot.send_message(message.chat.id, f"🚫 Вы не подписаны на [наш канал](https://t.me/{CHANNEL_ID[1:]})!\n"
                                          f"Подпишитесь, чтобы получить доступ ко всему функционалу.",
                         parse_mode="Markdown")
