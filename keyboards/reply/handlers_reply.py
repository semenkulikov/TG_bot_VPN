from telebot.types import ReplyKeyboardMarkup, KeyboardButton


def handlers_reply() -> ReplyKeyboardMarkup:
    keyboard = ReplyKeyboardMarkup(True, False, row_width=2,
                                   input_field_placeholder="Нажмите на нужную кнопку либо введите команду...")
    keyboard.add(KeyboardButton('🌍 Серверы'), KeyboardButton('❓ Справка'))
    keyboard.add(KeyboardButton('📖 Инструкция'))
    return keyboard
