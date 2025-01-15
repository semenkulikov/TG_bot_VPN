from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton


def is_subscribed_markup():
    """ Inline buttons для проверки подписки """
    actions = InlineKeyboardMarkup(row_width=1)
    actions.add(InlineKeyboardButton(text=f"Я подписался", callback_data="True"))
    return actions
