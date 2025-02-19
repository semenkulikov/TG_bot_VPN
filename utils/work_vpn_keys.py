from config_data.config import DEFAULT_SERVER_PASSWORD, XRAY_CONFIG_PATH, DEFAULT_SERVER_USER
from database.models import VPNKey, Server
from loader import app_logger
from utils.generate_vpn_keys import execute_ssh_command


def suspend_key(vpn_key: VPNKey) -> bool:
    """
    Приостанавливает действие ключа, удаляя его из конфигурации Xray на сервере.
    Обновляет статус is_valid в базе данных.
    """
    client_uuid = vpn_key.extract_uuid()
    if not client_uuid:
        app_logger.error(f"Не удалось извлечь UUID из ключа {vpn_key.id}")
        return False

    server = vpn_key.server
    try:
        # Удаление клиента из конфигурации с помощью jq
        remove_cmd = (
            f'echo {DEFAULT_SERVER_PASSWORD} | sudo -S sh -c '
            f'"jq \'del(.inbounds[0].settings.clients[] | select(.id == \\"{client_uuid}\\"))\' '
            f'{XRAY_CONFIG_PATH} > {XRAY_CONFIG_PATH}.tmp && '
            f'mv {XRAY_CONFIG_PATH}.tmp {XRAY_CONFIG_PATH}"'
        )
        output = execute_ssh_command(
            ip=server.ip_address,
            username=DEFAULT_SERVER_USER,
            password=DEFAULT_SERVER_PASSWORD,
            command=remove_cmd,
            timeout=30
        )
        app_logger.info(f"Клиент {client_uuid} удалён из конфига. Вывод: {output}")

        # Перезапуск Xray
        restart_output = execute_ssh_command(
            ip=server.ip_address,
            username=DEFAULT_SERVER_USER,
            password=DEFAULT_SERVER_PASSWORD,
            command=f'echo {DEFAULT_SERVER_PASSWORD} | sudo -S systemctl restart xray',
            timeout=30
        )
        app_logger.info(f"Xray перезапущен: {restart_output}")

        # Обновление статуса ключа
        vpn_key.is_valid = False
        vpn_key.save()
        return True
    except Exception as ex:
        app_logger.error(f"Ошибка при приостановке ключа {vpn_key.id}: {ex}")
        return False

def resume_key(vpn_key: VPNKey) -> bool:
    """
    Возобновляет действие ключа, добавляя его обратно в конфигурацию Xray.
    Обновляет статус is_valid в базе данных.
    """
    client_uuid = vpn_key.extract_uuid()
    if not client_uuid:
        app_logger.error(f"Не удалось извлечь UUID из ключа {vpn_key.id}")
        return False

    server = vpn_key.server
    try:
        # Добавление клиента в конфигурацию
        add_cmd = (
            f'echo {DEFAULT_SERVER_PASSWORD} | sudo -S sh -c '
            f'"jq \'.inbounds[0].settings.clients += [{{"id": "{client_uuid}", "flow": "xtls-rprx-vision"}}]\' '
            f'{XRAY_CONFIG_PATH} > {XRAY_CONFIG_PATH}.tmp && '
            f'mv {XRAY_CONFIG_PATH}.tmp {XRAY_CONFIG_PATH}"'
        )
        output = execute_ssh_command(
            ip=server.ip_address,
            username=DEFAULT_SERVER_USER,
            password=DEFAULT_SERVER_PASSWORD,
            command=add_cmd,
            timeout=30
        )
        app_logger.info(f"Клиент {client_uuid} добавлен в конфиг. Вывод: {output}")

        # Перезапуск Xray
        restart_output = execute_ssh_command(
            ip=server.ip_address,
            username=DEFAULT_SERVER_USER,
            password=DEFAULT_SERVER_PASSWORD,
            command=f'echo {DEFAULT_SERVER_PASSWORD} | sudo -S systemctl restart xray',
            timeout=30
        )
        app_logger.info(f"Xray перезапущен: {restart_output}")

        # Обновление статуса ключа
        vpn_key.is_valid = True
        vpn_key.save()
        return True
    except Exception as ex:
        app_logger.error(f"Ошибка при возобновлении ключа {vpn_key.id}: {ex}")
        return False

def revoke_key(vpn_key: VPNKey) -> bool:
    """
    Полностью отзывает ключ: удаляет из конфигурации Xray и из базы данных.
    """
    try:
        # Удаление из конфигурации
        if not suspend_key(vpn_key):
            return False

        # Удаление из базы данных
        vpn_key.delete_instance()
        app_logger.info(f"Ключ {vpn_key.id} полностью отозван.")
        return True
    except Exception as ex:
        app_logger.error(f"Ошибка при отзыве ключа {vpn_key.id}: {ex}")
        return False

def get_active_keys(server: Server) -> list[VPNKey]:
    """
    Возвращает список активных ключей для указанного сервера.
    """
    return list(server.keys.where(VPNKey.is_valid == True))

def get_inactive_keys(server: Server) -> list[VPNKey]:
    """
    Возвращает список неактивных ключей для указанного сервера.
    """
    return list(server.keys.where(VPNKey.is_valid == False))