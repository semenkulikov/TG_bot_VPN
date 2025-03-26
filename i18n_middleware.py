from contextvars import ContextVar
from typing import Optional
import gettext
from config_data.config import LOCALES_DIR

DOMAIN = 'messages'
_user_lang: ContextVar[Optional[str]] = ContextVar('user_lang', default='en')

def set_user_language(lang_code: str):
    """
    Устанавливает переводчик для текущего потока в зависимости от кода языка.
    Если язык не поддерживается или перевод не найден, используется английский.
    """
    lang_code = lang_code if lang_code in ['ru', 'en'] else 'en'
    _user_lang.set(lang_code)

def gettext_func(text: str) -> str:
    """
    Возвращает переведённую строку для текущего потока, либо оригинальный текст,
    если переводчик не установлен.
    """
    lang = _user_lang.get()
    try:
        translator = gettext.translation(DOMAIN, localedir=LOCALES_DIR, languages=[lang])
    except FileNotFoundError:
        translator = gettext.NullTranslations()
    return translator.gettext(text)

# Глобальная функция для перевода, которую будут использовать хендлеры.
_ = gettext_func
