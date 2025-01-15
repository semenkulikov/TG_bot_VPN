from telebot.handler_backends import State, StatesGroup


class AdminPanel(StatesGroup):
    get_users = State()

class SubscribedState(StatesGroup):
    subscribe = State()
