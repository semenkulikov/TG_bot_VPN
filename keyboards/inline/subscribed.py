from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from config_data.config import CHANNEL_ID


def is_subscribed_markup():
    """ Inline buttons для проверки подписки """
    actions = InlineKeyboardMarkup(row_width=2)
    actions.add(InlineKeyboardButton(text=f"Guard Tunnel VPN", url=f"https://t.me/{CHANNEL_ID[1:]}",
                                     callback_data="1"),
                InlineKeyboardButton(text=f" ✅ Я подписался", callback_data="2"))
    return actions

def get_renew_markup(vpn_key_id: int):
    """Возвращает inline-клавиатуру с кнопкой «Продлить ключ»."""
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton(text="🔄 Продлить ключ", callback_data=f"renew_{vpn_key_id}"))
    return markup
