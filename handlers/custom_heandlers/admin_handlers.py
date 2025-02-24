import os

import peewee
import qrcode
from telebot.types import Message
from config_data.config import ALLOWED_USERS, DEFAULT_COMMANDS, ADMIN_COMMANDS, QR_CODE_DIR
from database.models import User, Server, VPNKey
from keyboards.inline.admin_buttons import (
    users_markup,
    admin_markup,
    get_vpn_markup,
    get_servers_markup,
    delete_vpn_markup,
    key_actions_markup
)
from loader import bot, app_logger
from states.states import AdminPanel
from utils.functions import valid_ip, convert_amnezia_xray_json_to_vless_str, get_all_commands_bot
from utils.generate_vpn_keys import setup_server, generate_key
from utils.work_vpn_keys import suspend_key, resume_key, revoke_key, cleanup_server


@bot.message_handler(commands=["admin_panel"])
def admin_panel(message: Message):
    """ Хендлер для админ панели """
    if message.from_user.id in ALLOWED_USERS:
        app_logger.info(f"Администратор {message.from_user.full_name} зашел в админ панель.")
        bot.send_message(message.from_user.id, "🔧 Добро пожаловать в админ панель!\n\nВыберите нужную опцию ниже 👇",
                         reply_markup=admin_markup())
        bot.set_state(message.from_user.id, AdminPanel.get_option)
    else:
        bot.send_message(message.from_user.id, "❌ У вас недостаточно прав")
        app_logger.warning(f"Пользователь {message.from_user.full_name} пытался войти в админ панель")


@bot.callback_query_handler(func=None, state=AdminPanel.get_option)
def admin_panel_handler(call):
    """ Callback handler для выбора раздела админ панели """
    bot.answer_callback_query(callback_query_id=call.id)

    if call.data == "Exit":
        bot.send_message(call.message.chat.id, "🚪 Вы успешно вышли из админ панели. До встречи!")
        bot.set_state(call.message.chat.id, None)
        app_logger.info(f"Администратор {call.from_user.full_name} вышел из админ панели.")
    elif call.data == "users":
        app_logger.info(f"Администратор {call.from_user.full_name} зашел в юзер панель.")
        bot.send_message(call.message.chat.id, "👥 Список всех пользователей базы данных:", reply_markup=users_markup())
        bot.set_state(call.message.chat.id, AdminPanel.get_users)
    elif call.data == "servers":
        app_logger.info(f"Администратор {call.from_user.full_name} зашел в панель управления серверами.")
        bot.send_message(call.message.chat.id, "🖥 Панель управления серверами:", reply_markup=get_servers_markup())
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
        try:
            vpn_key: VPNKey = user_obj.vpn_key
            vpn_key = vpn_key.name
        except Exception:
            vpn_key = "отсутствует"
        app_logger.info(f"Администратор {call.from_user.full_name} запросил "
                        f"информацию о пользователе {user_obj.full_name}")
        bot.send_message(call.message.chat.id,
                         f"👤 Имя: {user_obj.full_name}\n"
                         f"📱 Телеграм: @{user_obj.username}\n"
                         f"📢 Подписан на канал: {user_obj.is_subscribed}\n"
                         f"🔑 VPN ключ: {vpn_key}"
                         )


@bot.callback_query_handler(func=None, state=AdminPanel.get_servers)
def server_panel_handler(call):
    """ Хендлер для управления серверами """
    bot.answer_callback_query(callback_query_id=call.id)

    if call.data == "Add":
        bot.send_message(call.message.chat.id,
                         "📄 Введите данные сервера в следующем формате:\n"
                         "🏙 Location (например, США)\n"
                         "👤 Username (например, root)\n"
                         "🔒 Password (пароль от root)\n"
                         "🌐 IP address"
                         )
        bot.set_state(call.message.chat.id, AdminPanel.add_server)
        return

    server_id = call.data
    server_obj: Server = Server.get_by_id(server_id)

    app_logger.info(f"Администратор {call.from_user.full_name} запросил информацию о сервере {server_obj.location}")

    # Проверка настроен ли сервер
    status = "✅ Настроен" if server_obj.public_key else "❌ Требует настройки"

    bot.send_message(call.message.chat.id,
                     f"🖥 Сервер: {server_obj.location}\n"
                     f"🔰 Статус: {status}\n"
                     f"🌐 IP адрес: {server_obj.ip_address}\n"
                     f"🔑 Количество ключей: {server_obj.keys.count()}",
                     reply_markup=get_vpn_markup(server_id))
    bot.set_state(call.message.chat.id, AdminPanel.get_vpn_keys)


@bot.message_handler(state=AdminPanel.add_server)
def add_server(message: Message):
    """ Добавление нового сервера """
    try:
        server_data = [item.strip() for item in message.text.split("\n")]
        if len(server_data) != 4:  # Убрали порт X-UI
            raise ValueError("❌ Неверное количество полей!")
        elif valid_ip(server_data[3]) is False:
            raise ValueError("❌ Неверный формат IP адреса!")

        # Создаем сервер и настраиваем
        server = Server.create(
            location=server_data[0],
            username=server_data[1],
            password=server_data[2],
            ip_address=server_data[3]
        )
        app_logger.info(f"Администратор {message.from_user.full_name} начинает настройку сервера {server.location}")
        bot.send_message(message.from_user.id, "Начинаю настройку сервера, подождите...")
        # Автоматическая настройка сервера
        if setup_server(server):
            bot.send_message(message.from_user.id, "✅ Сервер успешно настроен!")
        else:
            bot.send_message(message.from_user.id, "❌ Ошибка настройки сервера!")
            server.delete_instance()
            bot.set_state(message.from_user.id, None)
            return

        bot.set_state(message.from_user.id, None)
        app_logger.info(f"Администратор {message.from_user.full_name} добавил сервер {server.location}")

    except Exception as ex:
        bot.send_message(message.from_user.id, f"❌ Некорректные данные!\n{ex}")
        app_logger.error(f"Ошибка при добавлении сервера {ex}")
        bot.set_state(message.from_user.id, None)


@bot.callback_query_handler(func=None, state=AdminPanel.get_vpn_keys)
def vpn_panel_handler(call):
    """ Хендлер для управления всеми привязанными к серверу VPN ключами """
    bot.answer_callback_query(callback_query_id=call.id)

    if "Generate" in call.data:
        # Генерация нового ключа
        server_id = call.data.split()[1]
        server = Server.get_by_id(server_id)
        app_logger.info(f"Администратор {call.from_user.full_name} запросил генерацию"
                        f" VPN ключа для сервера {server.location}")
        bot.send_message(call.message.chat.id, f"⌛ Пожалуйста, подождите... Идет генерация нового VPN ключа...")
        key = generate_key(server)
        if key:
            bot.send_message(call.message.chat.id, f"✅ Отлично! VPN ключ «{key.name}» успешно создан!")
            app_logger.info(f"Администратор {call.from_user.full_name} успешно создал "
                            f"VPN ключ {key.name} для сервера {server.location}")
        else:
            bot.send_message(call.message.chat.id, "❌ Ошибка генерации ключа!")

        bot.set_state(call.message.chat.id, AdminPanel.get_vpn_keys)
        return

    if "Delete" in call.data:
        server_id = call.data.split()[1]
        server_obj: Server = Server.get_by_id(server_id)
        bot.send_message(call.message.chat.id, f"🗑 Начинается полная очистка сервера. Пожалуйста, подождите...")
        if cleanup_server(server_obj):
            app_logger.info(f"Администратор {call.from_user.full_name} удалил сервер {server_obj.location}")
            bot.send_message(call.message.chat.id, f"✅ Сервер {server_obj.location} успешно удалён вместе "
                                                   f"с привязанными VPN ключами!")
            bot.set_state(call.message.chat.id, AdminPanel.get_servers)
        else:
            bot.send_message(call.message.chat.id, "❌ Ошибка удаления сервера!")
            bot.set_state(call.message.chat.id, AdminPanel.get_servers)
        return

    if "VPN - " in call.data:
        # Выдача всей информации по VPN ключу
        vpn_obj: VPNKey = VPNKey.get_by_id(call.data.split("VPN - ")[1])
        app_logger.info(f"Администратор {call.from_user.full_name} запросил информацию о VPN ключе {vpn_obj.name}")
        status = "✅ Активен" if vpn_obj.is_valid else "⏸ Приостановлен / Занят"
        users = ", ".join([user.full_name for user in vpn_obj.users]) if vpn_obj.users else "Нет пользователей"
        text = (
            f"🔑 Ключ: {vpn_obj.name}\n"
            f"📍 Сервер: {vpn_obj.server.location}\n"
            f"📡 Статус: {status}\n"
            f"👤 Пользователи: {users}\n"
            f"🕒 Создан: {vpn_obj.created_at.strftime('%d.%m.%Y %H:%M')}"
        )

        # Отправляем QR-код если есть
        if os.path.exists(vpn_obj.qr_code):
            with open(vpn_obj.qr_code, 'rb') as qr_file:
                bot.send_photo(call.message.chat.id, qr_file, caption=text,
                               reply_markup=key_actions_markup(vpn_obj.id))
        else:
            bot.send_message(call.message.chat.id, text,
                             reply_markup=key_actions_markup(vpn_obj.id))
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

    if "action_" in call.data:
        action, key_id = call.data.split("_")[1], call.data.split("_")[2]
        vpn_key = VPNKey.get_by_id(key_id)

        if action == "suspend":
            app_logger.info(f"Администратор {call.message.from_user.full_name} запросил остановку "
                            f"VPN ключа {vpn_key.name}")
            if suspend_key(vpn_key):
                bot.send_message(call.message.chat.id, f"⏸ Ключ {vpn_key.name} приостановлен")
            else:
                bot.send_message(call.message.chat.id, "❌ Ошибка приостановки ключа!")

        elif action == "resume":
            app_logger.info(f"Администратор {call.message.from_user.full_name} запросил возобновление работы "
                            f"VPN ключа {vpn_key.name}")
            if resume_key(vpn_key):
                bot.send_message(call.message.chat.id, f"▶️ Ключ {vpn_key.name} возобновлен")
            else:
                bot.send_message(call.message.chat.id, "❌ Ошибка возобновления ключа!")

        elif action == "revoke":
            app_logger.info(f"Администратор {call.message.from_user.full_name} запросил отзыв "
                            f"VPN ключа {vpn_key.name}")
            if revoke_key(vpn_key):
                for user in User.select().where(User.vpn_key == vpn_key):
                    user.vpn_key = None
                    user.save()
                bot.send_message(call.message.chat.id, f"🗑 Ключ {vpn_key.name} отозван")
            else:
                bot.send_message(call.message.chat.id, "❌ Ошибка отзыва ключа!")

        bot.set_state(call.message.chat.id, AdminPanel.get_servers)
        return

    if "Cancel" in call.data:
        bot.send_message(call.message.chat.id, "Вы вернулись в админку.",
                         reply_markup=admin_markup())
        app_logger.info(f"Администратор {call.from_user.full_name} вернулся в админку")
        bot.set_state(call.message.chat.id, AdminPanel.get_option)
        return
    else:
        # Скорее всего, пользователь выбрал другой VPN ключ
        bot.set_state(call.message.chat.id, AdminPanel.get_vpn_keys)
        vpn_panel_handler(call)


@bot.message_handler(commands=["message_sending"])
def message_sending_handler(message: Message):
    """ Хендлер рассылки сообщений юзерам """
    if message.from_user.id in ALLOWED_USERS:
        app_logger.info(f"Администратор {message.from_user.full_name} вызвал команду /message_sending.")
        bot.send_message(message.from_user.id, "✉️ Введите текст сообщения для рассылки пользователям:")
        bot.set_state(message.from_user.id, AdminPanel.send_message)
    else:
        bot.send_message(message.from_user.id, "❌ У вас недостаточно прав для выполнения этой команды!")
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
    bot.send_message(message.chat.id, "✅ Рассылка сообщений завершена!")
    bot.set_state(message.from_user.id, None)


@bot.message_handler(commands=["add_vpn_key"])
def add_vpn_key_handler(message: Message):
    """ Хендлер для ручного добавления VPN ключа """
    if message.from_user.id in ALLOWED_USERS:
        app_logger.info(f"Администратор {message.from_user.full_name} вызвал команду /add_vpn_key.")
        bot.send_message(message.from_user.id, "🔑 Введите название нового VPN ключа:")
        bot.set_state(message.from_user.id, AdminPanel.add_vpn_key_name)
    else:
        bot.send_message(message.from_user.id, "У вас недостаточно прав!")


@bot.message_handler(state=AdminPanel.add_vpn_key_name)
def add_vpn_key_name_handler(message: Message):
    """ Обработка ввода названия VPN ключа """
    app_logger.info(f"Администратор {message.from_user.full_name} ввел название VPN ключа: {message.text}")
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data["vpn_key_name"] = message.text
    bot.send_message(message.from_user.id, "🔑 Введите VPN KEY в формате JSON или "
                                           "VLESS-ссылку (например, vless://...) :")
    bot.set_state(message.from_user.id, AdminPanel.add_vpn_key_key)


@bot.message_handler(state=AdminPanel.add_vpn_key_key)
def add_vpn_key_key_handler(message: Message):
    """ Обработка ввода VPN ключа """

    if message.text in get_all_commands_bot():
        bot.send_message(message.from_user.id, "Это одна из команд бота")
        bot.set_state(message.from_user.id, None)
        return

    app_logger.info(f"Администратор {message.from_user.full_name} ввел VPN ключ")
    if "vless://" not in message.text:
        vless_str = convert_amnezia_xray_json_to_vless_str(message.text)
        if vless_str is None:
            bot.send_message(message.from_user.id, "Не удалось преобразовать JSON в VLESS строку. "
                                                   "Проверьте правильность ввода.")
            app_logger.warning("Не удалось преобразовать json конфиг в vless строку!")
            return
    else:
        vless_str = message.text
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
        bot.send_message(call.message.chat.id,
                         "📄 Введите данные сервера в следующем формате:\n"
                         "🏙 Location (например, США)\n"
                         "👤 Username (например, root)\n"
                         "🔒 Password (пароль от root)\n"
                         "🌐 IP address"
                         )
        bot.set_state(call.message.chat.id, AdminPanel.add_server)
        return

    server_id = call.data
    server_obj: Server = Server.get_by_id(server_id)
    with bot.retrieve_data(call.from_user.id, call.from_user.id) as data:
        try:
            key_number = len(server_obj.keys) + 1 if hasattr(server_obj, "keys") else 1
            qr_code_filename = f"vpn_key_{server_obj.id}_{key_number}.png"
            qr_code_path = os.path.join(QR_CODE_DIR, qr_code_filename)
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_H,
                box_size=10,
                border=4
            )
            qr.add_data(data["vpn_key_key"])
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            img.save(qr_code_path)
            app_logger.info(f"QR-код сгенерирован и сохранён по пути: {qr_code_path}")
            vpn_key = VPNKey.create(
                name=data["vpn_key_name"],
                key=data["vpn_key_key"],
                qr_code=qr_code_path,
                server=server_obj,
            )
        except peewee.IntegrityError:
            bot.send_message(call.message.chat.id, "Такой ключ уже существует!")
            bot.send_message(call.message.chat.id, "Вы вышли в главное меню")
            app_logger.warning(f"Попытка создания дубликата VPN ключа {data['vpn_key_name']}!")

        else:
            app_logger.info(f"Администратор {call.message.from_user.full_name} добавил VPN ключ {vpn_key.name} "
                            f"к серверу {server_obj.location}")
            bot.send_message(call.message.chat.id, f"VPN ключ {vpn_key.name} добавлен к серверу {server_obj.location}.")
        bot.set_state(call.message.chat.id, None)
