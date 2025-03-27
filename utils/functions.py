from config_data.config import DEFAULT_COMMANDS, ADMIN_COMMANDS
from loader import bot, app_logger
import json
import os
import importlib.util
from database.models import Migration
from config_data.config import BASE_DIR


def is_subscribed(chat_id, user_id):
    """
    Проверяет, подписан ли пользователь на канал.
    Возвращает True, если статус входит в ("creator", "administrator", "member", "restricted").
    Если user_id некорректен, возвращает False.
    """
    try:
        # Приводим user_id к целому числу, если это возможно
        user_id = int(user_id)
    except (ValueError, TypeError):
        app_logger.error(f"Некорректный user_id: {user_id}")
        return False

    try:
        result = bot.get_chat_member(chat_id, user_id)
        if result.status in ("creator", "administrator", "member", "restricted"):
            return True
    except Exception as e:
        app_logger.error(f"Ошибка при получении информации о пользователе {user_id}: {e}")
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
    total_commands.extend(["🌍 Серверы", "❓ Справка", "📖 Инструкция", "🔧 Панель управления",
                           "🌍 Servers", "❓ Help", "📖 Instruction", "🔧 Control panel"])
    return total_commands


def run_migrations():
    migrations_dir = os.path.join(BASE_DIR, "migrations")
    if not os.path.exists(migrations_dir):
        app_logger.info("Папка миграций не найдена. Пропускаем миграции.")
        return
    migration_files = sorted([f for f in os.listdir(migrations_dir) if f.endswith(".py")])
    for filename in migration_files:
        try:
            # Проверяем, применена ли миграция
            Migration.get(Migration.name == filename)
            app_logger.info(f"Миграция {filename} уже применена.")
        except Migration.DoesNotExist:
            filepath = os.path.join(migrations_dir, filename)
            spec = importlib.util.spec_from_file_location("migration_module", filepath)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            if hasattr(module, "run_migration"):
                module.run_migration()
                Migration.create(name=filename)
                app_logger.info(f"Миграция {filename} успешно применена.")
            else:
                app_logger.error(f"В файле {filename} отсутствует функция run_migration().")
