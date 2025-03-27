from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from database.models import User
from i18n_middleware import _


def user_panel_markup(user_obj: User):
    """ Inline buttons для выбора ключей """
    actions = InlineKeyboardMarkup(row_width=1)


    for uv_obj in user_obj.vpn_keys:
        actions.add(InlineKeyboardButton(text=f"🔑 {uv_obj.vpn_key.name}",
                                         callback_data=f"VPN - {str(uv_obj.vpn_key.id)}"))
    actions.add(InlineKeyboardButton(text=_("🚪 Выйти"), callback_data="Cancel"))
    return actions


def user_key_actions_markup(key_id: int) -> InlineKeyboardMarkup:
    """
    Клавиатура для управления ключом:
    - Приостановить/возобновить
    - Назад
    """
    markup = InlineKeyboardMarkup(row_width=2)

    markup.add(
        InlineKeyboardButton(_("🗑 Отозвать"), callback_data=f"action_revoke_{key_id}"),
        InlineKeyboardButton(_("🔙 Назад"), callback_data="Exit")
    )
    return markup
