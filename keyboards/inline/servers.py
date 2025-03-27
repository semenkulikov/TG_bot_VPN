from typing import List

from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from database.models import Server, UserVPNKey
from i18n_middleware import _


def get_locations_markup():
    """ Inline buttons для выдачи всех локаций серверов """
    actions = InlineKeyboardMarkup(row_width=1)
    servers_obj = Server.select()
    for server in servers_obj:
        actions.add(InlineKeyboardButton(text=f"🌍 {server.location}", callback_data=str(server.id)))
    return actions

def get_instruction_markup():
    """ Inline buttons для выдачи ссылки на инструкцию """
    actions = InlineKeyboardMarkup(row_width=1)
    actions.add(InlineKeyboardButton(text=_("📖 Инструкция для подключения"), url="https://telegra.ph/"
                                                                              "Kak-ispolzovat-VPN-servis-"
                                                                              "Guard-Tunnel-01-16"))
    return actions


def get_deleted_key_markup(user_keys: List[UserVPNKey]):
    """ Inline buttons для выбора ключа, который надо удалить """
    markup = InlineKeyboardMarkup(row_width=1)
    for uv in user_keys:
        markup.add(InlineKeyboardButton(
            text=f"{uv.vpn_key.name}",
            callback_data=f"remove_key_{uv.vpn_key.id}"
        ))
    return markup
