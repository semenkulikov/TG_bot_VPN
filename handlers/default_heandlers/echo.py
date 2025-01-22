from telebot.types import Message
from loader import bot
from handlers.custom_heandlers.location_handlers import location_handler
from handlers.default_heandlers.help import bot_help
from handlers.custom_heandlers.instruction_handlers import instruction_handler


# Эхо хендлер, куда летят текстовые сообщения без указанного состояния

@bot.message_handler(state=None)
def bot_echo(message: Message):
    if message.text == "Серверы":
        location_handler(message)
    elif message.text == "Справка":
        bot_help(message)
    elif message.text == "Инструкция":
        instruction_handler(message)
    else:
        bot.reply_to(message, f"Введите любую команду из меню, чтобы я начал работать\n"
                              f"Либо выберите одну из кнопок, которые я вам прислал")

