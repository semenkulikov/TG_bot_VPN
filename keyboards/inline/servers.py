from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from database.models import Server


def get_locations_markup():
    """ Inline buttons для выдачи всех локаций серверов """
    actions = InlineKeyboardMarkup(row_width=1)
    servers_obj = Server.select()
    for server in servers_obj:
        actions.add(InlineKeyboardButton(text=f"🌍 {server.location}", callback_data=str(server.id)))
    return actions
