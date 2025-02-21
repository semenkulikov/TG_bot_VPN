from config_data.config import DEFAULT_COMMANDS, ADMIN_COMMANDS
from loader import bot, app_logger
import json



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


def valid_ip(address):
    try:
        host_bytes = address.split('.')
        valid = [int(b) for b in host_bytes]
        valid = [b for b in valid if 0 <= b <= 255]
        return len(host_bytes) == 4 and len(valid) == 4
    except (TypeError, ValueError, IndexError):
        return False

def convert_amnezia_xray_json_to_vless_str(amnezia_str: str) -> str | None:
    """
    Функция для конвертации AMnezia Xray JSON в VLESS строчку
    :param amnezia_str: JSON-строка с настройками Amnezia Xray
    :return: VLESS-строка либо None объект
    """
    try:
        json_object = json.loads(amnezia_str)
    except Exception:
        app_logger.error("Не удалось преобразовать JSON в объект!")
        return None
    try:
        outbounds = json_object["outbounds"][0]["settings"]["vnext"][0]
        stream_settings = json_object["outbounds"][0]["streamSettings"]

        address_and_port = f"{outbounds['address']}:{outbounds['port']}"
        flow = outbounds["users"][0]["flow"]
        user_id = outbounds["users"][0]["id"]
        type_of_net = stream_settings["network"]
        security = stream_settings["security"]
        fp = stream_settings["realitySettings"]["fingerprint"]
        pbk = stream_settings["realitySettings"]["publicKey"]
        sni = stream_settings["realitySettings"]["serverName"]
        sid = stream_settings["realitySettings"]["shortId"]

        url = (f"vless://{user_id}@{address_and_port}?flow={flow}&type={type_of_net}&"
               f"security={security}&fp={fp}&sni={sni}&pbk={pbk}&sid={sid}")
    except Exception as ex:
        app_logger.error(f"Не получилось конвертировать конфиг Amnezia!\n{ex}")
        return None
    return url

def get_all_commands_bot():
    total_commands = [f"/{elem[0]}" for elem in DEFAULT_COMMANDS]
    total_commands.extend([f"/{elem[0]}" for elem in ADMIN_COMMANDS])
    total_commands.extend(["🌍 Серверы", "❓ Справка", "📖 Инструкция"])
    return total_commands
