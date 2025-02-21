from telebot.types import Message

from config_data.config import DEFAULT_COMMANDS, ADMIN_COMMANDS, ALLOWED_USERS
from loader import bot


@bot.message_handler(commands=['help'])
def bot_help(message: Message):
    commands = [f"/{command} - {description}" for command, description in DEFAULT_COMMANDS]
    if message.from_user.id in ALLOWED_USERS:
        commands.extend([f"/{command} - {description}" for command, description in ADMIN_COMMANDS])
    bot.reply_to(message, "📋 Доступные команды:\n" + "\n".join(commands))
    bot.send_message(message.chat.id, "🤝 Для поддержки обращайтесь: @guardtunnel_support")
