from telebot.types import Message
from loader import bot, app_logger
from config_data.config import DEFAULT_COMMANDS, ADMIN_COMMANDS, ALLOWED_USERS, CHANNEL_ID
from database.models import User, Group
from utils.functions import is_subscribed
from keyboards.inline.subscribed import is_subscribed_markup
from keyboards.reply.handlers_reply import handlers_reply
from states.states import SubscribedState
from i18n_middleware import _


start_text = ("*Вы не подписались на канал!*\n"
"\n"
"☺️ Для доступа к полному функционалу бота вам необходимо подписаться на наш новостной канал [Guard Tunnel VPN](https://t.me/{channel_id})\n"
"\n"
"🎁 В подарок вы получите *бесплатный доступ* на использование нашего сервиса\n"
"\n"
"*С Уважением, команда Guard Tunnel VPN*\n"
"\n"
"_После подписки на наш канал нажмите ниже на кнопку: ✅ Я подписался_")


@bot.message_handler(commands=['start'])
def bot_start(message: Message):
    if message.chat.type == "private":
        is_sub = True if message.from_user.id in ALLOWED_USERS else False
        if User.get_or_none(user_id=message.from_user.id) is None:
            app_logger.info(f"Внимание! Новый юзер: {message.from_user.full_name} - {message.from_user.username}")
            User.create(user_id=message.from_user.id,
                        full_name=message.from_user.full_name,
                        username=message.from_user.username if message.from_user.username is not None else "None",
                        is_premium=message.from_user.is_premium,
                        is_subscribed=is_sub)
        commands = [f"/{command} - {_(description)}" for command, description in DEFAULT_COMMANDS]
        if message.from_user.id in ALLOWED_USERS:
            commands.extend([f"/{command} - {_(description)}" for command, description in ADMIN_COMMANDS])
            bot.send_message(
                message.from_user.id,
                _("Здравствуйте, {full_name}! 👋\n"
                "Вы вошли как администратор. Доступны следующие команды:\n{commands}").format(
                    full_name=message.from_user.full_name,
                    commands='\n'.join(commands)
                ),
                reply_markup=handlers_reply()
            )
        else:
            if is_subscribed(CHANNEL_ID, message.from_user.id):
                # Если пользователь подписан на канал, тогда ему можно пользоваться ботом.
                bot.send_message(message.from_user.id, _("Приветствуем, {full_name}.\n"
                                                       "Рады приветствовать вас на нашем сервисе!\n"
                                                       "Что бы использовать наш VPN сервис, "
                                                       "следуйте инструкциям ниже 👇\n"
                                                       "{commands}").format(
                    full_name=message.from_user.full_name,
                    commands='\n'.join(commands)
                ),
                                 reply_markup=handlers_reply())
                cur_user = User.get(User.user_id == message.from_user.id)
                cur_user.is_subscribed = True
                cur_user.save()
            else:
                bot.send_message(message.from_user.id, _(start_text).format(channel_id=CHANNEL_ID[1:]),
                                 reply_markup=is_subscribed_markup(), parse_mode='Markdown',
                                 disable_web_page_preview=True)
                cur_user = User.get(User.user_id == message.from_user.id)
                cur_user.is_subscribed = False
                cur_user.save()
                bot.set_state(message.from_user.id, SubscribedState.subscribe)

    else:
        bot.send_message(message.chat.id, _("Здравствуйте! Я - телеграм бот, модератор каналов и групп. "
                                          "Чтобы получить больше информации, "
                                          "обратитесь к администратору, или напишите мне в личку)"))
        if Group.get_or_none(group_id=message.chat.id) is None:
            Group.create(group_id=message.chat.id,
                         title=message.chat.title,
                         description=message.chat.description,
                         bio=message.chat.bio,
                         invite_link=message.chat.invite_link,
                         location=message.chat.location,
                         username=message.chat.username)
            app_logger.info(f"Внимание! Новая группа: {message.chat.title} - {message.chat.invite_link}")
        if User.get_or_none(user_id=message.from_user.id) is None:
            User.create(user_id=message.from_user.id,
                        full_name=message.from_user.full_name,
                        username=message.from_user.username,
                        is_premium=message.from_user.is_premium)
            app_logger.info(f"Внимание! Новый юзер: {message.from_user.full_name} - {message.from_user.username}")

@bot.callback_query_handler(func=None, state=SubscribedState.subscribe)
def is_subscribed_handler(call):
    if is_subscribed(CHANNEL_ID, call.from_user.id):
        commands = [f"/{command} - {_(description)}" for command, description in DEFAULT_COMMANDS]
        app_logger.info(f"Пользователь {call.from_user.full_name} подписался на канал!")

        cur_user = User.get(User.user_id == call.from_user.id)
        cur_user.is_subscribed = True
        cur_user.save()

        bot.answer_callback_query(callback_query_id=call.id)
        bot.send_message(call.message.chat.id, _("Спасибо, что выбрали наш сервис, приятного использования!\n"
                                               f"Вам доступны следующие команды:\n"
                                               "{commands}").format(
            commands='\n'.join(commands)
        ))
        bot.set_state(call.message.chat.id, None)
    else:
        bot.answer_callback_query(callback_query_id=call.id)
        bot.send_message(call.message.chat.id, _(start_text).format(channel_id=CHANNEL_ID[1:]),
                         reply_markup=is_subscribed_markup(), parse_mode='Markdown',
                         disable_web_page_preview=True)
