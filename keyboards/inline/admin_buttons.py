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


def users_markup(page: int = 1, per_page: int = 10) -> InlineKeyboardMarkup:
    """
    Inline-клавиатура для выбора пользователя с пагинацией.
    Отображаются пользователи, у которых user_id не входит в ALLOWED_USERS.
    """
    offset = (page - 1) * per_page
    # Получаем на одну запись больше, чтобы проверить наличие следующей страницы
    users_query = User.select().where(
        User.user_id.not_in(ALLOWED_USERS)
    ).order_by(User.full_name).offset(offset).limit(per_page + 1)
    users_list = list(users_query)
    has_next = len(users_list) > per_page
    if has_next:
        users_list = users_list[:per_page]

    markup = InlineKeyboardMarkup(row_width=2)
    for user in users_list:
        # Используем префикс "user_" для кнопок выбора пользователя
        markup.add(InlineKeyboardButton(text=f"👤 {user.full_name}", callback_data=f"user_{user.id}"))

    # Добавляем кнопки пагинации, если нужно
    pagination_buttons = []
    if page > 1:
        pagination_buttons.append(InlineKeyboardButton(text="⬅️ Назад",
                                                       callback_data=f"users_page_{page - 1}"))
    if has_next:
        pagination_buttons.append(InlineKeyboardButton(text="Вперед ➡️",
                                                       callback_data=f"users_page_{page + 1}"))
    if pagination_buttons:
        markup.row(*pagination_buttons)
    markup.add(InlineKeyboardButton(text="🔙 Выйти", callback_data="Exit_to_admin_panel"))
    return markup


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