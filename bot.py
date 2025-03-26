from telebot.handler_backends import BaseMiddleware
from i18n_middleware import set_user_language

class I18nMiddleware(BaseMiddleware):
    def __init__(self):
        super().__init__()
        # self.update_sensitive = True
        self.update_types = ['message', 'callback_query']

    def pre_process(self, message, data):
        if message.text:
            lang = getattr(message.from_user, 'language_code', 'en')
            set_user_language(lang)
        elif message.callback_query:
            lang = getattr(message.callback_query.from_user, 'language_code', 'en')
            set_user_language(lang)

    def post_process(self, message, data, exception):
        pass