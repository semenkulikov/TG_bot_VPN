from telebot.types import Message
from database.models import User, Server, VPNKey
from loader import bot, app_logger
from keyboards.inline.servers import get_locations_markup
from states.states import GetVPNKey
from utils.generate_vpn_keys import generate_key


@bot.message_handler(commands=["location"])
def location_handler(message: Message):
    """ Хендлер для выбора сервера подключения """
    app_logger.info(f"Пользователь {message.from_user.full_name} вызвал команду /location")
    cur_user = User.get(User.user_id == message.from_user.id)

    if cur_user.is_subscribed:
        bot.send_message(message.chat.id, "Выберите сервер подключения:", reply_markup=get_locations_markup())
        bot.set_state(message.chat.id, GetVPNKey.get_server)
    else:
        bot.send_message(message.chat.id, "Вы не подписаны на канал!")


@bot.callback_query_handler(func=None, state=GetVPNKey.get_server)
def get_server_handler(call):
    """ Хендлер для получения сервера подключения """
    bot.answer_callback_query(callback_query_id=call.id)

    server_id = call.data

    cur_user: User = User.get(User.user_id == call.from_user.id)
    cur_server: Server = Server.get_by_id(server_id)

    # Проверка на то, что текущий VPN ключ пользователя удален.
    try:
        VPNKey.get_by_id(cur_user.vpn_key)
    except Exception:
        app_logger.warning(f"Внимание! У пользователя {cur_user.full_name} не нашлось ключа VPN!")
        cur_user.vpn_key = None
        cur_user.save()

    app_logger.info(f"Пользователь {cur_user.full_name} выбрал сервер {cur_server.location}")

    # Получение всех vpn ключей данного сервера и выбор одного
    for vpn_key_obj in cur_server.keys:
        if vpn_key_obj.is_valid:
            if cur_user.vpn_key is not None:
                users_vpn = VPNKey.get_by_id(cur_user.vpn_key)
                users_vpn.is_valid = True
                users_vpn.save()
                app_logger.info(f"VPN ключ {users_vpn.name} теперь свободен.")
            cur_user.vpn_key = vpn_key_obj
            cur_user.save()
            vpn_key_obj.is_valid = False
            vpn_key_obj.save()
            app_logger.info(f"Пользователь {cur_user.full_name} зарезервировал ключ {vpn_key_obj.name}")
            # with open(vpn_key_obj.qr_code, "rb") as qr_code:
            #     bot.send_photo(call.message.chat.id, qr_code,
            #                      f"Мы не собираем и не храним информацию о подключениях к серверам!\n\n"
            #                      f"URL для подключения:\n\n{vpn_key_obj.key}")
            bot.send_message(call.message.chat.id, f"Мы не собираем и не храним информацию о подключениях к серверам!\n\n"
                                                        f"Имя ключа: {vpn_key_obj.name}\n"
                                                   f"Сервер: {cur_server.location}\n"
                                                   f"URL для подключения:\n\n{vpn_key_obj.key}")
            bot.set_state(call.message.chat.id, None)
            return

    # Если нет свободных ключей, генерируем новый
    app_logger.warning(f"Внимание! Для сервера {cur_server.location} не нашлось свободных VPN ключей! "
                       f"Генерирую новый...")

    # Заглушка на пока что.
    bot.send_message(call.message.chat.id, "К сожалению, для данного сервера пока нет свободных ключей.")
    if cur_user.vpn_key is not None:
        bot.send_message(call.message.chat.id, f"Ваш текущий ключ: {cur_user.vpn_key.name}\n"
                                               f"URL для подключения:\n\n{cur_user.vpn_key.key}")
    return

    new_key: VPNKey = generate_key(cur_server)
    app_logger.info(f"Сгенерирован новый ключ {new_key.name}!")

    if cur_user.vpn_key is not None:
        users_vpn = VPNKey.get_by_id(cur_user.vpn_key)
        users_vpn.is_valid = True
        users_vpn.save()
        app_logger.info(f"VPN ключ {users_vpn.name} теперь свободен.")

    cur_user.vpn_key = new_key
    cur_user.save()

    new_key.is_valid = False
    new_key.save()
    app_logger.info(f"Пользователь {cur_user.full_name} зарезервировал новый ключ {new_key.name}")
    # with open(new_key.qr_code, "rb") as qr_code:
    #     bot.send_photo(call.message.chat.id, qr_code,
    #                      f"Мы не собираем и не храним информацию о подключениях к серверам!\n\n"
    #                      f"URL для подключения:\n\n{new_key.key}")
    bot.send_message(call.message.chat.id, f"Мы не собираем и не храним информацию о подключениях к серверам!\n\n"
                                           f"Имя ключа: {vpn_key_obj.name}\n"
                                           f"Сервер: {cur_server.location}\n"
                                           f"URL для подключения:\n\n{vpn_key_obj.key}")
    bot.set_state(call.message.chat.id, None)
