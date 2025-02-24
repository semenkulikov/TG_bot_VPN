import os

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

        # Удаление QR-кода, если он существует
        if os.path.exists(vpn_key.qr_code):
            os.remove(vpn_key.qr_code)

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


def cleanup_server(server: Server) -> bool:
    """Полная очистка сервера от Xray и конфигов, с подробным логированием."""
    app_logger.info(f"Администратор запросил полное удаление севрера {server.location}. Начинаю очистку...")
    try:
        cmds = [
            # Остановка и отключение службы Xray
            f"echo {DEFAULT_SERVER_PASSWORD} | sudo -S systemctl stop xray",
            f"echo {DEFAULT_SERVER_PASSWORD} | sudo -S systemctl disable xray",
            # Удаление Xray с помощью официального скрипта
            f"echo {DEFAULT_SERVER_PASSWORD} | sudo -S bash -c 'curl -sL https://raw.githubusercontent.com/XTLS/Xray-install/main/install-release.sh | bash -s -- remove'",
            # Очистка пакетов и конфигов
            f"echo {DEFAULT_SERVER_PASSWORD} | sudo -S apt-get purge xray -y",
            f"echo {DEFAULT_SERVER_PASSWORD} | sudo -S rm -rf /usr/local/etc/xray/",
            # Восстановление фаервола: удаление правила для 443/tcp
            f"echo {DEFAULT_SERVER_PASSWORD} | sudo -S ufw delete allow 443/tcp",
            # Удаление созданного пользователя
            f"echo {DEFAULT_SERVER_PASSWORD} | sudo -S pkill -9 -u {DEFAULT_SERVER_USER} || true",
            f"echo {DEFAULT_SERVER_PASSWORD} | sudo -S userdel -rf {DEFAULT_SERVER_USER} || true",
            # Очистка cron задач
            f"echo {DEFAULT_SERVER_PASSWORD} | sudo -S crontab -u {DEFAULT_SERVER_USER} -r || true"
        ]
        full_output = ""
        for cmd in cmds:
            output = execute_ssh_command(
                ip=server.ip_address,
                username=DEFAULT_SERVER_USER,
                password=DEFAULT_SERVER_PASSWORD,
                command=cmd,
                timeout=60
            )
            full_output += f"\nКоманда: {cmd}\nВывод: {output}"

        # Удаляем запись о сервере из БД
        server.delete_instance()

        # Удаление связанных VPN ключей
        for vpn_key in VPNKey.select().where(VPNKey.server == server):
            for user in vpn_key.users:
                user.vpn_key = None
                user.save()
            app_logger.info(f"VPN ключ {vpn_key.name} удален!")
            vpn_key.delete_instance()

        app_logger.info(f"Cleanup завершён. Общий вывод: {full_output}")
        return True
    except Exception as ex:
        app_logger.error(f"Server cleanup failed: {ex}")
        return False