from telebot.types import ReplyKeyboardMarkup, KeyboardButton
from i18n_middleware import _


def handlers_reply() -> ReplyKeyboardMarkup:
    keyboard = ReplyKeyboardMarkup(True, False, row_width=2,
                                   input_field_placeholder=_("Нажмите на нужную кнопку либо введите команду..."))
    keyboard.add(KeyboardButton(_('🌍 Серверы')), KeyboardButton(_('❓ Справка')))
    keyboard.add(KeyboardButton(_('📖 Инструкция')))
    keyboard.add(KeyboardButton(_('🔧 Панель управления')))
    return keyboard
