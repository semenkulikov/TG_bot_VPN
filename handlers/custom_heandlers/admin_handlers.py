from telebot.types import Message
import datetime
from config_data.config import ALLOWED_USERS, DEFAULT_COMMANDS, ADMIN_COMMANDS
from database.models import User, Server, VPNKey
from keyboards.inline.admin_buttons import (users_markup, admin_markup, get_vpn_markup,
                                            get_servers_markup, delete_vpn_markup)
from loader import bot, app_logger
from states.states import AdminPanel
from utils.functions import valid_ip, convert_amnezia_xray_json_to_vless_str, get_all_commands_bot


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
        app_logger.warning(f"Пользователь {message.from_user.full_name} пытался войти в админ панель")


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
    bot.answer_callback_query(callback_query_id=call.id)
    if call.data == "Exit":

        bot.send_message(call.message.chat.id, "Выберите опцию", reply_markup=admin_markup())
        bot.set_state(call.message.chat.id, AdminPanel.get_option)
        app_logger.info(f"Администратор {call.from_user.full_name} вернулся обратно к выбору опций.")
    else:
        user_obj: User = User.get_by_id(call.data)
        vpn_key: VPNKey = VPNKey.get_or_none(user_obj.vpn_key)
        app_logger.info(f"Администратор {call.from_user.full_name} запросил "
                        f"информацию о пользователе {user_obj.full_name}")
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

    app_logger.info(f"Администратор {call.from_user.full_name} запросил информацию о сервере {server_obj.location}")
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

    if message.text in get_all_commands_bot():
        bot.send_message(message.from_user.id, "Это одна из команд бота")
        bot.set_state(message.from_user.id, None)
        return

    try:
        server_data = [item.strip() for item in message.text.split("\n")]
        if len(server_data)!= 5:
            raise ValueError("Неверное количество полей!")
        elif valid_ip(server_data[3]) is False:
            raise ValueError("Неверный формат IP адреса!")

        Server.create(location=server_data[0], username=server_data[1], password=server_data[2],
                     ip_address=server_data[3], port=server_data[4])

        bot.send_message(message.from_user.id, "Сервер добавлен.")
        bot.set_state(message.from_user.id, None)

        app_logger.info(f"Администратор {message.from_user.full_name} добавил сервер {server_data[0]}")
    except Exception as ex:
        bot.send_message(message.from_user.id, f"Некорректные данные!\n{ex}")
        bot.set_state(message.from_user.id, AdminPanel.add_server)
        app_logger.error(f"Ошибка при добавлении сервера {ex}")


@bot.callback_query_handler(func=None, state=AdminPanel.get_vpn_keys)
def vpn_panel_handler(call):
    """ Хендлер для управления всеми привязанными к серверу VPN ключами """
    bot.answer_callback_query(callback_query_id=call.id)

    if "Delete" in call.data:
        server_id = call.data.split()[1]
        server_obj: Server = Server.get_by_id(server_id)
        server_obj.delete_instance()
        app_logger.info(f"Администратор {call.from_user.full_name} удалил сервер {server_obj.location}")
        bot.send_message(call.message.chat.id, f"Сервер {server_obj.location} удален.")
        bot.set_state(call.message.chat.id, AdminPanel.get_servers)
        return

    if "VPN - " in call.data:
        # Выдача всей информации по VPN ключу
        vpn_obj: VPNKey = VPNKey.get_by_id(call.data.split("VPN - ")[1])
        app_logger.info(f"Администратор {call.from_user.full_name} запросил информацию о VPN ключе {vpn_obj.name}")
        bot.send_message(call.message.chat.id, f"Имя: {vpn_obj.name}\n"
                                                f"Сервер: {Server.get_by_id(vpn_obj.server).location}\n"
                                               f"VPN KEY: {vpn_obj.key}\n"
                                               f"Свободен: {"Да" if vpn_obj.is_valid else "Нет"}\n"
                                               f"Пользователи: {", ".join([user.full_name for user in vpn_obj.users])}\n"
                                               f"Создан: {vpn_obj.created_at}",
                         reply_markup=delete_vpn_markup(vpn_obj.id))
        bot.set_state(call.message.chat.id, AdminPanel.delete_vpn)
    elif "Cancel" in call.data:
        # Возврат в меню серверов
        bot.send_message(call.message.chat.id, "Вы вернулись в меню серверов.",
                         reply_markup=get_servers_markup())
        app_logger.info(f"Администратор {call.from_user.full_name} вернулся в меню серверов")
        bot.set_state(call.message.chat.id, AdminPanel.get_servers)
    else:
        bot.set_state(call.message.chat.id, AdminPanel.get_vpn_keys)

@bot.callback_query_handler(func=None, state=AdminPanel.delete_vpn)
def vpn_panel_handler(call):
    """ Хендлер для удаления VPN ключа """
    bot.answer_callback_query(callback_query_id=call.id)
    if "Cancel" in call.data:
        bot.send_message(call.message.chat.id, "Вы вернулись в админку.",
                         reply_markup=admin_markup())
        app_logger.info(f"Администратор {call.from_user.full_name} вернулся в админку")
        bot.set_state(call.message.chat.id, AdminPanel.get_option)
        return
    if "Del - " in call.data:
        vpn_key_id = int(call.data.split(" - ")[1])
        vpn_obj: VPNKey = VPNKey.get_by_id(vpn_key_id)
        bot.send_message(call.message.chat.id, f"VPN ключ {vpn_obj.name} удален.")
        app_logger.info(f"Администратор удалил VPN ключ {vpn_obj.name}")
        vpn_obj.delete_instance()

        bot.set_state(call.message.chat.id, AdminPanel.get_servers)
    else:
        # Скорее всего, пользователь выбрал другой VPN ключ
        bot.set_state(call.message.chat.id, AdminPanel.get_vpn_keys)
        vpn_panel_handler(call)


@bot.message_handler(commands=["message_sending"])
def message_sending_handler(message: Message):
    """ Хендлер рассылки сообщений юзерам """
    if message.from_user.id in ALLOWED_USERS:
        app_logger.info(f"Администратор {message.from_user.full_name} вызвал команду /message_sending.")
        bot.send_message(message.from_user.id, "Введите сообщение для рассылки")
        bot.set_state(message.from_user.id, AdminPanel.send_message)
    else:
        bot.send_message(message.from_user.id, "У вас недостаточно прав")
        app_logger.warning(f"Попытка доступа к /message_sending без прав администратора {message.from_user.full_name}")


@bot.message_handler(state=AdminPanel.send_message)
def send_message_to_users_handler(message: Message):
    """ Отправка сообщений пользователям """
    # Проверка, что сообщение для рассылки - не одна из команд бота

    if message.text in get_all_commands_bot():
        bot.send_message(message.from_user.id, "Это одна из команд бота")
        bot.set_state(message.from_user.id, None)
        return

    # Проверка, что сообщение не пустое
    if not message.text:
        bot.send_message(message.from_user.id, "Сообщение не может быть пустым.")
        return
    app_logger.info(f"Администратор {message.from_user.full_name} начал рассылку сообщений: {message.text}")

    bot.send_message(message.chat.id, "Начинаю рассылку...")
    bot.send_chat_action(message.chat.id, "typing")
    for user_obj in User.select():
        if int(user_obj.user_id) not in ALLOWED_USERS:
            bot.send_message(user_obj.user_id, message.text)
    bot.send_message(message.chat.id, "Рассылка сообщений завершена!")
    bot.set_state(message.from_user.id, None)


@bot.message_handler(commands=["add_vpn_key"])
def add_vpn_key_handler(message: Message):
    """ Хендлер для ручного добавления VPN ключа """
    if message.from_user.id in ALLOWED_USERS:
        app_logger.info(f"Администратор {message.from_user.full_name} вызвал команду /add_vpn_key.")
        bot.send_message(message.from_user.id, "Введите название VPN ключа")
        bot.set_state(message.from_user.id, AdminPanel.add_vpn_key_name)
    else:
        bot.send_message(message.from_user.id, "У вас недостаточно прав!")


@bot.message_handler(state=AdminPanel.add_vpn_key_name)
def add_vpn_key_name_handler(message: Message):
    """ Обработка ввода названия VPN ключа """
    app_logger.info(f"Администратор {message.from_user.full_name} ввел название VPN ключа: {message.text}")
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data["vpn_key_name"] = message.text
    bot.send_message(message.from_user.id, "Введите VPN KEY в формате json, не ссылка")
    bot.set_state(message.from_user.id, AdminPanel.add_vpn_key_key)


@bot.message_handler(state=AdminPanel.add_vpn_key_key)
def add_vpn_key_key_handler(message: Message):
    """ Обработка ввода VPN ключа """

    if message.text in get_all_commands_bot():
        bot.send_message(message.from_user.id, "Это одна из команд бота")
        bot.set_state(message.from_user.id, None)
        return

    app_logger.info(f"Администратор {message.from_user.full_name} ввел VPN ключ")
    vless_str = convert_amnezia_xray_json_to_vless_str(message.text)
    if vless_str is None:
        bot.send_message(message.from_user.id, "Не удалось преобразовать JSON в VLESS строку. "
                                               "Проверьте правильность ввода.")
        app_logger.warning("Не удалось преобразовать json конфиг в vless строку!")
        return
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data["vpn_key_key"] = vless_str
    bot.send_message(message.from_user.id, "Выберите сервер, к которому принадлежит ключ",
                     reply_markup=get_servers_markup())
    bot.set_state(message.from_user.id, AdminPanel.save_vpn_key)


@bot.callback_query_handler(func=None, state=AdminPanel.save_vpn_key)
def save_vpn_handler(call):
    """ Хендлер для сохранения в БД VPN ключа """
    bot.answer_callback_query(callback_query_id=call.id)

    if call.data == "Add":
        bot.send_message(call.message.chat.id, "Введите данные сервера в таком формате:\n"
                                               "Location (США например)\n"
                                               "Username (root к примеру)\n"
                                               "Password (пароль от root)\n"
                                               "IP address\n"
                                               "Порт работы ssh")
        bot.set_state(call.message.chat.id, AdminPanel.add_server)
        return

    server_id = call.data
    server_obj: Server = Server.get_by_id(server_id)
    with bot.retrieve_data(call.from_user.id, call.from_user.id) as data:
        vpn_key = VPNKey.create(
            name=data["vpn_key_name"],
            key=data["vpn_key_key"],
            qr_code=data["vpn_key_key"],  # Заглушка, потом будут нормальные пути
            server=server_obj,
        )
        app_logger.info(f"Администратор {call.message.from_user.full_name} добавил VPN ключ {vpn_key.name} "
                        f"к серверу {server_obj.location}")
        bot.send_message(call.message.chat.id, f"VPN ключ {vpn_key.name} добавлен к серверу {server_obj.location}.")
        bot.set_state(call.message.chat.id, None)
