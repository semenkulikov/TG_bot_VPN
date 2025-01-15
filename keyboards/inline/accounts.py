from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

from config_data.config import ALLOWED_USERS
from database.models import User


def users_markup():
    """ Inline buttons для выбора юзера """
    users_obj = User.select()
    actions = InlineKeyboardMarkup(row_width=2)

    for user in users_obj:
        if user.user_id not in ALLOWED_USERS:
            actions.add(InlineKeyboardButton(text=f"{user.full_name}", callback_data=user.id))
    actions.add(InlineKeyboardButton(text=f"Выйти", callback_data="Exit"))
    return actions
