from telebot.apihelper import ApiTelegramException
from loader import bot



def is_subscribed(chat_id, user_id):
    """
    Функция для проверки, подписан ли пользователь на канал.
    :param chat_id: id канала
    :param user_id: id пользователя
    :return: bool
    """
    result = bot.get_chat_member(chat_id, user_id)
    if result.status in ("creator", "administrator", "member", "restricted"):
        return True
    return False
