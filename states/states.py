from telebot.handler_backends import State, StatesGroup


class AdminPanel(StatesGroup):
    get_option = State()
    get_users = State()
    get_servers = State()
    add_server = State()
    get_vpn_keys = State()
    delete_server = State()
    delete_vpn = State()
    send_message = State()

    add_vpn_key_name = State()
    add_vpn_key_key = State()
    save_vpn_key = State()


class SubscribedState(StatesGroup):
    subscribe = State()

class GetVPNKey(StatesGroup):
    get_server = State()
    get_key = State()
