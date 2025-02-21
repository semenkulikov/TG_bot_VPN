from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

from config_data.config import ALLOWED_USERS
from database.models import User, Server


def admin_markup():
    """ Inline buttons для выбора меню админа """
    actions = InlineKeyboardMarkup(row_width=2)
    actions.add(InlineKeyboardButton(text=f"🖥 Управление серверами", callback_data="servers"))
    actions.add(InlineKeyboardButton(text=f"👥 Управление пользователями", callback_data="users"))
    actions.add(InlineKeyboardButton(text=f"🚪 Выйти", callback_data="Exit"))
    return actions


def users_markup():
    """ Inline buttons для выбора юзера """
    users_obj = User.select()
    actions = InlineKeyboardMarkup(row_width=2)

    for user in users_obj:
        if int(user.user_id) not in ALLOWED_USERS:
            actions.add(InlineKeyboardButton(text=f"👤 {user.full_name}", callback_data=user.id))
    actions.add(InlineKeyboardButton(text=f"🔙 Назад", callback_data="Exit"))
    return actions


def get_servers_markup():
    """ Inline buttons для выдачи всех локаций серверов """
    actions = InlineKeyboardMarkup(row_width=1)
    servers_obj = Server.select()
    for server in servers_obj:
        actions.add(InlineKeyboardButton(text=f"🌍 {server.location}", callback_data=str(server.id)))
    actions.add(InlineKeyboardButton(text=f"➕ Добавить сервер", callback_data="Add"))
    return actions

def get_vpn_markup(server_id):
    """ Inline buttons для выдачи vpn ключей сервера """
    cur_server: Server = Server.get_by_id(server_id)
    actions = InlineKeyboardMarkup(row_width=2)
    for vpn_key_obj in cur_server.keys:
        actions.add(InlineKeyboardButton(text=f"🔑 {vpn_key_obj.name}", callback_data=f"VPN - {str(vpn_key_obj.id)}"))
    actions.add(InlineKeyboardButton(text=f"🔄 Сгенерировать новый ключ", callback_data=f"Generate {cur_server.id}"))
    actions.add(InlineKeyboardButton(text=f"🗑 Удалить сервер", callback_data=f"Delete {cur_server.id}"),
                InlineKeyboardButton(text=f"🔙 Назад", callback_data="Cancel"))  # Возврат в меню серверов
    return actions

def delete_vpn_markup(vpn_obj_id: int):
    """ Inline buttons для удаления vpn ключа """
    actions = InlineKeyboardMarkup(row_width=2)
    actions.add(InlineKeyboardButton(text=f"🗑 Удалить", callback_data=f"Del - {vpn_obj_id}"),
                InlineKeyboardButton(text=f"🚪 Выйти", callback_data="Cancel"))
    return actions


def key_actions_markup(key_id: int) -> InlineKeyboardMarkup:
    """
    Клавиатура для управления ключом:
    - Приостановить/возобновить
    - Отозвать
    - Назад
    """
    markup = InlineKeyboardMarkup(row_width=2)

    markup.add(
        InlineKeyboardButton("⏸ Приостановить", callback_data=f"action_suspend_{key_id}"),
        InlineKeyboardButton("▶️ Возобновить", callback_data=f"action_resume_{key_id}"),
        InlineKeyboardButton("🗑 Отозвать", callback_data=f"action_revoke_{key_id}"),
        InlineKeyboardButton("🔙 Назад", callback_data="Cancel")
    )
    return markup