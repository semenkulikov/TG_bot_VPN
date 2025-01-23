from telebot.types import Message
import datetime
from config_data.config import ALLOWED_USERS
from database.models import User, Server, VPNKey
from keyboards.inline.admin_buttons import (users_markup, admin_markup, get_vpn_markup,
                                            get_servers_markup, delete_vpn_markup)
from loader import bot, app_logger
from states.states import AdminPanel


@bot.message_handler(commands=["admin_panel"])
def admin_panel(message: Message):
    """ Хендлер для админ панели """
    if message.from_user.id in ALLOWED_USERS:
        app_logger.info(f"Администратор {message.from_user.full_name} зашел в админ панель.")
        bot.send_message(message.from_user.id, "Вы вошли в админ панель. Выберите кнопку ниже",
                         reply_markup=admin_markup())
        bot.set_state(message.from_user.id, AdminPanel.get_option)
    else:
        bot.send_message(message.from_user.id, "У вас недостаточно прав")


@bot.callback_query_handler(func=None, state=AdminPanel.get_option)
def admin_panel_handler(call):
    """ Callback handler для выбора раздела админ панели """
    bot.answer_callback_query(callback_query_id=call.id)

    if call.data == "Exit":
        bot.send_message(call.message.chat.id, "Вы успешно вышли из админ панели.")
        bot.set_state(call.message.chat.id, None)
        app_logger.info(f"Администратор {call.from_user.full_name} вышел из админ панели.")
    elif call.data == "users":
        app_logger.info(f"Администратор {call.from_user.full_name} зашел в юзер панель.")
        bot.send_message(call.message.chat.id, "Все пользователи базы данных:", reply_markup=users_markup())
        bot.set_state(call.message.chat.id, AdminPanel.get_users)
    elif call.data == "servers":
        app_logger.info(f"Администратор {call.from_user.full_name} зашел в панель управления серверами.")
        bot.send_message(call.message.chat.id, "Панель управления серверами:", reply_markup=get_servers_markup())
        bot.set_state(call.message.chat.id, AdminPanel.get_servers)


@bot.callback_query_handler(func=None, state=AdminPanel.get_users)
def get_user(call):
    """ Хендлер для работы с юзерами из админ панели """
    if call.data == "Exit":
        bot.answer_callback_query(callback_query_id=call.id)
        bot.send_message(call.message.chat.id, "Выберите опцию", reply_markup=admin_markup())
        bot.set_state(call.message.chat.id, AdminPanel.get_option)
        app_logger.info(f"Администратор {call.from_user.full_name} вернулся обратно к выбору опций.")
    else:
        bot.answer_callback_query(callback_query_id=call.id)
        user_obj: User = User.get_by_id(call.data)
        vpn_key: VPNKey = VPNKey.get_or_none(user_obj.vpn_key)
        if vpn_key is not None:
            vpn_key = vpn_key.name
        bot.send_message(call.message.chat.id, f"Имя: {user_obj.full_name}\n"
                                               f"Телеграм: @{user_obj.username}\n"
                                               f"Подписан на канал: {user_obj.is_subscribed}\n"
                                               f"VPN ключ: {vpn_key}")


@bot.callback_query_handler(func=None, state=AdminPanel.get_servers)
def server_panel_handler(call):
    """ Хендлер для управления серверами """
    bot.answer_callback_query(callback_query_id=call.id)

    if call.data == "Add":
        bot.send_message(call.message.chat.id, "Введите данные сервера в таком формате:\n"
                                               "Location (США например)\n"
                                               "Username (root к примеру)\n"
                                               "Password (пароль от root)\n"
                                               "IP address\n"
                                               "Port работы X-UI")
        bot.set_state(call.message.chat.id, AdminPanel.add_server)
        return

    server_id = call.data
    server_obj: Server = Server.get_by_id(server_id)


    # Выдача всей информации по серверу
    bot.send_message(call.message.chat.id, f"Имя сервера: {server_obj.location}\n"
                                               f"Username: {server_obj.username}\n"
                                               f"Password: {server_obj.password}\n"
                                               f"IP адрес: {server_obj.ip_address}\n"
                                               f"Порт работы X-UI: {server_obj.port}\n"
                                               f"VPN ключи, привязанные к данному серверу:",
                     reply_markup=get_vpn_markup(server_id))
    bot.set_state(call.message.chat.id, AdminPanel.get_vpn_keys)


@bot.message_handler(state=AdminPanel.add_server)
def add_server(message: Message):
    """ Добавление нового сервера """
    try:
        server_data = message.text.split("\n")
        Server.create(location=server_data[0], username=server_data[1], password=server_data[2],
                     ip_address=server_data[3], port=server_data[4])

        bot.send_message(message.from_user.id, "Сервер добавлен.")
        bot.set_state(message.from_user.id, None)

        app_logger.info(f"Администратор {message.from_user.full_name} добавил сервер {server_data[0]}")
    except Exception:
        bot.send_message(message.from_user.id, "Некорректные данные!!")
        bot.set_state(message.from_user.id, AdminPanel.add_server)
        app_logger.error(f"Ошибка при добавлении сервера {message.text}")


@bot.callback_query_handler(func=None, state=AdminPanel.get_vpn_keys)
def vpn_panel_handler(call):
    """ Хендлер для управления всеми привязанными к серверу VPN ключами """
    bot.answer_callback_query(callback_query_id=call.id)

    if "Delete" in call.data:
        server_id = call.data.split()[1]
        server_obj: Server = Server.get_by_id(server_id)
        server_obj.delete_instance()
        bot.send_message(call.message.chat.id, f"Сервер {server_obj.location} удален.")
        bot.set_state(call.message.chat.id, AdminPanel.get_servers)
        return

    # Выдача всей информации по VPN ключу
    vpn_obj: VPNKey = VPNKey.get_by_id(call.data)
    bot.send_message(call.message.chat.id, f"Имя: {vpn_obj.name}\n"
                                            f"Сервер: {Server.get_by_id(vpn_obj.server).location}\n"
                                           f"VPN KEY: {vpn_obj.key}\n"
                                           f"Занят: {"Да" if vpn_obj.is_valid else "Нет"}\n"
                                           f"Пользователи: {", ".join([user.full_name for user in vpn_obj.users])}\n"
                                           f"Создан: {vpn_obj.created_at}",
                     reply_markup=delete_vpn_markup(vpn_obj.id))
    bot.set_state(call.message.chat.id, AdminPanel.delete_vpn)


@bot.callback_query_handler(func=None, state=AdminPanel.delete_vpn)
def vpn_panel_handler(call):
    """ Хендлер для удаления VPN ключа """
    bot.answer_callback_query(callback_query_id=call.id)
    if "Cancel" in call.data:
        bot.send_message(call.message.chat.id, "Вы вернулись в админку.",
                         reply_markup=admin_markup())
        bot.set_state(call.message.chat.id, AdminPanel.get_option)
        return
    if "Del - " in call.data:
        vpn_key_id = int(call.data.split(" - ")[1])
        vpn_obj: VPNKey = VPNKey.get_by_id(vpn_key_id)
        bot.send_message(call.message.chat.id, f"VPN ключ {vpn_obj.name} удален.")
        app_logger.info(f"Администратор удалил VPN ключ {vpn_obj.name}")
        vpn_obj.delete_instance()

        bot.set_state(call.message.chat.id, AdminPanel.get_servers)


@bot.message_handler(commands=["message_sending"])
def message_sending_handler(message: Message):
    """ Хендлер рассылки сообщений юзерам """
    if message.from_user.id in ALLOWED_USERS:
        app_logger.info(f"Администратор {message.from_user.full_name} вызвал команду /message_sending.")
        bot.send_message(message.from_user.id, "Введите сообщение для рассылки")
        bot.set_state(message.from_user.id, AdminPanel.send_message)
    else:
        bot.send_message(message.from_user.id, "У вас недостаточно прав")


@bot.message_handler(state=AdminPanel.send_message)
def send_message_to_users_handler(message: Message):
    """ Отправка сообщений пользователям """
    app_logger.info(f"Администратор {message.from_user.full_name} начал рассылку сообщений: {message.text}")

    bot.send_message(message.chat.id, "Начинаю рассылку...")
    bot.send_chat_action(message.chat.id, "typing")
    for user_obj in User.select():
        if int(user_obj.user_id) not in ALLOWED_USERS:
            bot.send_message(user_obj.user_id, message.text)
    bot.send_message(message.chat.id, "Рассылка сообщений завершена!")
    bot.set_state(message.from_user.id, None)