from telebot.types import Message
from loader import bot, app_logger
from config_data.config import DEFAULT_COMMANDS, ADMIN_COMMANDS, ALLOWED_USERS
from database.models import User, Group


@bot.message_handler(commands=['start'])
def bot_start(message: Message):
    if message.chat.type == "private":
        if User.get_or_none(user_id=message.from_user.id) is None:
            User.create(user_id=message.from_user.id,
                        full_name=message.from_user.full_name,
                        username=message.from_user.username,
                        is_premium=message.from_user.is_premium)
        commands = [f"/{command} - {description}" for command, description in DEFAULT_COMMANDS]
        if message.from_user.id in ALLOWED_USERS:
            commands.extend([f"/{command} - {description}" for command, description in ADMIN_COMMANDS])
            bot.send_message(message.from_user.id, f"Здравствуйте, {message.from_user.full_name}! "
                                                   f"Вы в списке администраторов бота. "
                                                   f"Вам доступны следующие команды:\n"
                                                   f"{'\n'.join(commands)}")
        else:
            app_logger.info(f"Внимание! Новый юзер: {message.from_user.full_name} - {message.from_user.username}")
            bot.send_message(message.from_user.id, f"Здравствуйте, {message.from_user.full_name}! "
                                                   f"Я - телеграм бот. "
                                                   f"Вам доступны следующие команды:\n"
                                                   f"{'\n'.join(commands)}")

    else:
        bot.send_message(message.chat.id, "Здравствуйте! Я - телеграм бот, модератор каналов и групп. "
                                          "Чтобы получить больше информации, "
                                          "обратитесь к администратору, или напишите мне в личку)")
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
