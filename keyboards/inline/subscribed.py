from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from config_data.config import CHANNEL_ID


def is_subscribed_markup():
    """ Inline buttons для проверки подписки """
    actions = InlineKeyboardMarkup(row_width=2)
    actions.add(InlineKeyboardButton(text=f"Guard Tunnel VPN", url=f"https://t.me/{CHANNEL_ID[1:]}",
                                     callback_data="1"),
                InlineKeyboardButton(text=f" ✅ Я подписался", callback_data="2"))
    return actions


def get_renew_markup_for_user(user_id: str):
    """
    Возвращает inline-клавиатуру с кнопкой продления для пользователя.
    В callback_data будем передавать 'renew_user_{user_id}'
    """
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton(text="🔄 Продлить ключи", callback_data=f"renew_user_{user_id}"))
    return markup
