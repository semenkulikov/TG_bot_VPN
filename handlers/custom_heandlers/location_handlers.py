from telebot.types import Message

from config_data.config import CHANNEL_ID
from database.models import User, Server, VPNKey, UserVPNKey
from loader import bot, app_logger, scheduler
from keyboards.inline.servers import get_locations_markup, get_instruction_markup, get_deleted_key_markup
from states.states import GetVPNKey
from utils.functions import is_subscribed
from utils.generate_vpn_keys import generate_key
from utils.tasks import cancel_key_revocation_for_user
from utils.work_vpn_keys import revoke_key
from i18n_middleware import _


@bot.message_handler(commands=["location"])
def location_handler(message: Message):
    """ Хендлер для выбора сервера подключения """
    app_logger.info(f"Пользователь {message.from_user.full_name} вызвал команду /location")
    cur_user = User.get(User.user_id == message.from_user.id)

    if is_subscribed(CHANNEL_ID, message.from_user.id):
        cur_user.is_subscribed = True
        bot.send_message(message.chat.id, _("🌍 Пожалуйста, выберите сервер для подключения:"),
                         reply_markup=get_locations_markup())
        bot.set_state(message.chat.id, GetVPNKey.get_server)
    else:
        bot.send_message(message.chat.id, _("🚫 Вы не подписаны на [наш канал](https://t.me/{channel_id})!\n"
                                            "Подпишитесь, чтобы получить доступ ко всему функционалу.").format(
            channel_id=CHANNEL_ID[1:]
        ),
                         parse_mode="Markdown")
        cur_user.is_subscribed = False
    cur_user.save()


@bot.callback_query_handler(func=None, state=GetVPNKey.get_server)
def get_server_handler(call):
    """ Хендлер для получения сервера подключения """
    bot.answer_callback_query(callback_query_id=call.id)

    server_id = call.data

    cur_user: User = User.get(User.user_id == call.from_user.id)
    cur_server: Server = Server.get_by_id(server_id)

    app_logger.info(f"Пользователь {cur_user.full_name} выбрал сервер {cur_server.location}")

    # Получаем список активных ключей пользователя (через связь many-to-many)
    user_keys = list(cur_user.vpn_keys)
    if len(user_keys) >= 3:
        # Лимит достигнут: предлагаем выбрать ключ для замены

        bot.send_message(
            call.message.chat.id,
            _("⚠️ У вас уже 3 активных VPN ключа.\nВыберите ключ, который хотите заменить:"),
            reply_markup=get_deleted_key_markup(user_keys)
        )
        # Сохраняем выбранный сервер в данных пользователя для дальнейшей генерации нового ключа
        with bot.retrieve_data(call.from_user.id, call.message.chat.id) as data:
            data["server_id"] = server_id
        bot.set_state(call.message.chat.id, GetVPNKey.choose_key_to_replace)
        return

    # Если лимит не достигнут – пытаемся найти свободный ключ на сервере
    available_key = None
    for vpn_key_obj in cur_server.keys:
        if vpn_key_obj.is_valid:
            available_key = vpn_key_obj
            break

    if available_key:
        # Привязываем найденный ключ к пользователю: создаём запись в промежуточной таблице
        UserVPNKey.create(user=cur_user, vpn_key=available_key)
        available_key.is_valid = False
        available_key.save()
        app_logger.info(f"Пользователь {cur_user.full_name} зарезервировал ключ {available_key.name}")
        with open(available_key.qr_code, "rb") as qr_code:
            caption = _(
                "🔒 Мы не храним информацию о ваших подключениях!\n\n"
                "🔑 Имя ключа: <b>{name}</b>\n"
                "🌍 Сервер: <b>{location}</b>\n"
                "🔗 URL для подключения:\n<code>{key}</code>"
            ).format(
                name=available_key.name,
                location=cur_server.location,
                key=available_key.key
            )
            bot.send_photo(
                call.message.chat.id,
                qr_code,
                caption=caption,
                parse_mode="HTML",
                reply_markup=get_instruction_markup()
            )
        bot.set_state(call.message.chat.id, None)
        return

    # Если нет свободных ключей, генерируем новый
    app_logger.warning(f"Для сервера {cur_server.location} не найдено свободных VPN ключей! Генерирую новый...")
    bot.send_message(
        call.message.chat.id,
        _("⌛ Пожалуйста, подождите... Идет генерация нового VPN ключа...")
    )

    new_key: VPNKey = generate_key(cur_server)
    if new_key is None:
        app_logger.error("Не удалось сгенерировать новый ключ!")
        bot.send_message(
            call.message.chat.id,
            _("❌ Ведутся технические работы на стороне сервера, поэтому генерация нового ключа пока невозможна!"
            "\nПопробуйте позже 😊")
        )
        bot.set_state(call.message.chat.id, None)
        return
    app_logger.info(f"Сгенерирован новый ключ {new_key.name}!")

    # Привязываем новый ключ пользователю
    UserVPNKey.create(user=cur_user, vpn_key=new_key)
    new_key.is_valid = False
    new_key.save()
    app_logger.info(f"Пользователь {cur_user.full_name} зарезервировал новый ключ {new_key.name}")
    with open(new_key.qr_code, "rb") as qr_code:
        caption = _(
            "🔒 Мы не храним информацию о ваших подключениях!\n\n"
            "🔑 Имя ключа: <b>{name}</b>\n"
            "🌍 Сервер: <b>{location}</b>\n"
            "🔗 URL для подключения:\n<code>{key}</code>"
        ).format(
            name=new_key.name,
            location=cur_server.location,
            key=new_key.key
        )
        bot.send_photo(
            call.message.chat.id,
            qr_code,
            caption=caption,
            parse_mode="HTML",
            reply_markup=get_instruction_markup()
        )
    bot.set_state(call.message.chat.id, None)


@bot.callback_query_handler(func=lambda call: call.data.startswith("remove_key_"),
                            state=GetVPNKey.choose_key_to_replace)
def remove_key_handler(call):
    """ Callback хендлер для выбора, какой VPN ключ удалить (при достижении лимита) """
    bot.answer_callback_query(callback_query_id=call.id)

    vpn_key_id = call.data.split("_")[2]
    vpn_key = VPNKey.get_by_id(vpn_key_id)
    # Отзываем выбранный ключ

    app_logger.info(f"Пользователь {call.from_user.full_name} выбрал замену ключа {vpn_key.name}")

    # Удаляем связь между пользователем и этим ключом
    UserVPNKey.delete().where(UserVPNKey.vpn_key == vpn_key,
                              UserVPNKey.user == User.get(User.user_id == call.from_user.id)).execute()
    if revoke_key(vpn_key):
        bot.send_message(call.message.chat.id, _("✅ VPN ключ «{name}» удален").format(
            name=vpn_key.name
        ))
        app_logger.info(f"Ключ {vpn_key.name} отозван по выбору пользователя {call.from_user.full_name}")
    else:
        bot.send_message(call.message.chat.id, _("❌ Ошибка при отзыве ключа!"))
        app_logger.error(f"Ошибка при отзыве ключа {vpn_key.name}!")
        bot.set_state(call.message.chat.id, None)
        return

    # Получаем сохранённый ранее server_id
    with bot.retrieve_data(call.from_user.id, call.message.chat.id) as data:
        server_id = data.get("server_id")
    if not server_id:
        bot.send_message(call.message.chat.id, _("❌ Ошибка: не найден сервер для генерации нового ключа."))
        bot.set_state(call.message.chat.id, None)
        return

    cur_server: Server = Server.get_by_id(server_id)
    # Генерируем новый ключ для этого сервера
    bot.send_message(
        call.message.chat.id,
        _("⌛ Пожалуйста, подождите... Идет генерация нового VPN ключа...")
    )
    new_key: VPNKey = generate_key(cur_server)
    if new_key is None:
        app_logger.error("Не удалось сгенерировать новый ключ!")
        bot.send_message(call.message.chat.id,
                         _("❌ Ведутся технические работы на стороне сервера, поэтому генерация нового ключа пока невозможна!"
                           "\nПопробуйте позже 😊"))
        bot.set_state(call.message.chat.id, None)
        return

    cur_user: User = User.get(User.user_id == call.from_user.id)

    # Привязываем новый ключ пользователю
    UserVPNKey.create(user=cur_user, vpn_key=new_key)
    new_key.is_valid = False
    new_key.save()
    app_logger.info(f"Пользователь {cur_user.full_name} заменил ключ {vpn_key.name} на новый ключ {new_key.name}")
    with open(new_key.qr_code, "rb") as qr_code:
        caption = _(
            "🔒 Мы не храним информацию о ваших подключениях!\n\n"
            "🔑 Имя ключа: <b>{name}</b>\n"
            "🌍 Сервер: <b>{location}</b>\n"
            "🔗 URL для подключения:\n<code>{key}</code>"
        ).format(
            name=new_key.name,
            location=cur_server.location,
            key=new_key.key
        )
        bot.send_photo(
            call.message.chat.id,
            qr_code,
            caption=caption,
            parse_mode="HTML",
            reply_markup=get_instruction_markup()
        )
    bot.set_state(call.message.chat.id, None)


@bot.callback_query_handler(func=lambda call: call.data.startswith("renew_user_"))
def renew_keys_handler(call):
    bot.answer_callback_query(callback_query_id=call.id)
    try:
        user_id = call.data.split("_")[2]
        user_obj = User.get(User.user_id == user_id)
        # Отменяем запланированную задачу отзыва для этого пользователя
        cancel_key_revocation_for_user(user_obj, scheduler)
        bot.send_message(call.message.chat.id,
                         _("✅ Ваши VPN ключи успешно продлены!"))
        app_logger.info(f"VPN ключи пользователя {user_obj.full_name} успешно продлены.")
    except Exception as e:
        app_logger.error(f"Ошибка при продлении ключей для пользователя {call.from_user.full_name}: {e}")
        bot.send_message(call.message.chat.id, _("❌ Произошла ошибка при продлении ключей."))
