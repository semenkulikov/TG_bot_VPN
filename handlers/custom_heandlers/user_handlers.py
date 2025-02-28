import os

from telebot.types import Message

from config_data.config import CHANNEL_ID
from database.models import User, VPNKey, UserVPNKey
from keyboards.inline.users import user_panel_markup, user_key_actions_markup
from loader import bot, app_logger
from states.states import UserPanel
from utils.work_vpn_keys import revoke_key


@bot.message_handler(commands=["panel"])
def user_panel(message: Message):
    """ Хендлер для юзер панели """
    cur_user = User.get(User.user_id == message.from_user.id)

    if cur_user.is_subscribed:
        app_logger.info(f"Пользователь {message.from_user.full_name} зашел в юзер панель.")
        bot.send_message(message.from_user.id, "🔧 Вы зашли в панель управления!\n\n"
                                               "<b>Профиль</b>\n"
                                                f"👤 Имя: {cur_user.full_name}\n"
                                                f"📱 Телеграм: @{cur_user.username}\n"
                                                f"📢 Подписан на канал: {cur_user.is_subscribed}\n\n"
                                               "🔑 Ваши VPN ключи 👇",
                         reply_markup=user_panel_markup(cur_user),
                         parse_mode="HTML")
        bot.set_state(message.from_user.id, UserPanel.get_keys)
    else:
        bot.send_message(message.chat.id, f"🚫 Вы не подписаны на [наш канал](https://t.me/{CHANNEL_ID[1:]})!\n"
                                          f"Подпишитесь, чтобы получить доступ ко всему функционалу.",
                         parse_mode="Markdown")


@bot.callback_query_handler(func=None, state=UserPanel.get_keys)
def user_keys_handler(call):
    """ Хендлер для управления всеми привязанными к серверу VPN ключами """
    bot.answer_callback_query(callback_query_id=call.id)

    if "VPN - " in call.data:
        # Выдача всей информации по VPN ключу
        vpn_obj: VPNKey = VPNKey.get_by_id(call.data.split("VPN - ")[1])
        app_logger.info(f"Пользователь {call.from_user.full_name} запросил информацию о VPN ключе {vpn_obj.name}")
        status = "✅ Активен"

        text = (
            f"🔑 Ключ: {vpn_obj.name}\n"
            f"📍 Сервер: {vpn_obj.server.location}\n"
            f"📡 Статус: {status}\n"
            f"🕒 Создан: {vpn_obj.created_at.strftime('%d.%m.%Y %H:%M')}\n\n"
            f"🔗 URL для подключения:\n`{vpn_obj.key}`"
        )

        if os.path.exists(vpn_obj.qr_code):
            with open(vpn_obj.qr_code, 'rb') as qr_file:
                bot.send_photo(call.message.chat.id, qr_file, caption=text,
                               parse_mode="Markdown",
                               reply_markup=user_key_actions_markup(vpn_obj.id))
        else:
            bot.send_message(call.message.chat.id, text,
                             reply_markup=user_key_actions_markup(vpn_obj.id))
        bot.set_state(call.message.chat.id, UserPanel.delete_vpn)
    elif "Cancel" in call.data:
        # Возврат в меню серверов
        bot.send_message(call.message.chat.id, "✅ Вы вернулись в главное меню")
        app_logger.info(f"Пользователь {call.from_user.full_name} вернулся в главное меню")
        bot.set_state(call.message.chat.id, None)
    else:
        bot.set_state(call.message.chat.id, None)


@bot.callback_query_handler(func=None, state=UserPanel.delete_vpn)
def user_vpn_delete_handler(call):
    """ Хендлер для управления VPN ключами (действия над ключом) пользователем """
    bot.answer_callback_query(callback_query_id=call.id)
    cur_user = User.get(User.user_id == call.from_user.id)

    if "action_" in call.data:
        action, key_id = call.data.split("_")[1], call.data.split("_")[2]
        vpn_key = VPNKey.get_by_id(key_id)

        if action == "revoke":
            app_logger.info(f"Пользователь {call.message.from_user.full_name} запросил отзыв VPN ключа {vpn_key.name}")

            UserVPNKey.delete().where(UserVPNKey.vpn_key == vpn_key).execute()
            bot.send_message(call.message.chat.id,
                             f"⌛ Пожалуйста, подождите... Идет удаление ключа {vpn_key.name}...")
            if revoke_key(vpn_key):
                bot.send_message(call.message.chat.id, f"🗑 Ключ {vpn_key.name} отозван")
                bot.send_message(call.message.chat.id, "🔑 Ваши VPN ключи 👇",
                                 reply_markup=user_panel_markup(cur_user),
                                 parse_mode="HTML")
            else:
                bot.send_message(call.message.chat.id, "❌ Ошибка отзыва ключа!")
        bot.set_state(call.message.chat.id, UserPanel.get_keys)

    elif "Exit" in call.data:
        bot.send_message(call.message.chat.id, "Вы вернулись в панель управления.")
        bot.send_message(call.message.chat.id, "🔑 Ваши VPN ключи 👇",
                         reply_markup=user_panel_markup(cur_user),
                         parse_mode="HTML")
        app_logger.info(f"Пользователь {call.from_user.full_name} вернулся в панель управления")
        bot.set_state(call.message.chat.id, UserPanel.get_keys)
        return
    else:
        bot.set_state(call.message.chat.id, None)
        bot.send_message(call.message.chat.id, "Команда не распознана. Вы были возвращены в главное меню")
