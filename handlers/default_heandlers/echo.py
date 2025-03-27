from telebot.types import Message

from handlers.custom_heandlers.user_handlers import user_panel
from loader import bot
from handlers.custom_heandlers.location_handlers import location_handler
from handlers.default_heandlers.help import bot_help
from handlers.custom_heandlers.instruction_handlers import instruction_handler
from i18n_middleware import _


# Эхо хендлер, куда летят текстовые сообщения без указанного состояния

@bot.message_handler(state=None)
def bot_echo(message: Message):
    if message.text in ("🌍 Серверы", "🌍 Servers"):
        location_handler(message)
    elif message.text in ("❓ Справка", "❓ Help"):
        bot_help(message)
    elif message.text in ("📖 Инструкция", "📖 Instruction"):
        instruction_handler(message)
    elif message.text in ("🔧 Панель управления", "🔧 Control panel"):
        user_panel(message)
    else:
        bot.reply_to(message, _("Введите любую команду из меню, чтобы я начал работать\n"
                              "Либо выберите одну из кнопок, которые я вам прислал 👇"))

