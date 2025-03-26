from telebot.handler_backends import BaseMiddleware
from i18n_middleware import set_user_language


class I18nMiddleware(BaseMiddleware):
    def __init__(self):
        super().__init__()
        # self.update_sensitive = True
        self.update_types = ['message', 'callback_query']

    def pre_process(self, message, data):
        if hasattr(message, 'from_user'):
            user = message.from_user
        elif hasattr(message, 'from_user'):
            user = message.from_user
        else:
            return

        lang = getattr(user, 'language_code', 'en') or 'en'  # Если language_code = None → 'en'
        set_user_language(lang)

    def post_process(self, message, data, exception):
        pass
