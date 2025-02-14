# import socket
# from typing import Optional
# import paramiko
# import pexpect
# from pexpect import pxssh
# from database.models import VPNKey, Server
# import os
# from config_data.config import BASE_DIR, DEFAULT_SERVER_USER, DEFAULT_SERVER_PASSWORD
# from loader import app_logger
#
#
# basic_config_server_sh = """
# # echo 'Hello, world!' && whoami &&
# sudo apt install jq openssl &&
# curl -L https://codeload.github.com/EvgenyNerush/easy-xray/tar.gz/main | tar -xz &&
# cd easy-xray-main &&
# chmod +x ex.sh &&
# sudo ./ex.sh install &&
# sudo ./ex.sh conf
# """
#
#
# user_settings = f"""
# sudo useradd -m -s /bin/bash -G sudo {DEFAULT_SERVER_USER} &&
# passwd {DEFAULT_SERVER_USER}
# """
#
# test_script = """
# """
#
#
# def execute_ssh_command(
#     ip: str,
#     username: str,
#     password: str,
#     command: str,
#     timeout: int = 120
# ) -> Optional[str]:
#     try:
#         with paramiko.SSHClient() as cl:
#             cl.load_system_host_keys()
#             cl.set_missing_host_key_policy(paramiko.RejectPolicy())
#             cl.connect(
#                 hostname=ip,
#                 username=username,
#                 password=password,
#                 look_for_keys=False,
#                 allow_agent=False,
#                 timeout=10
#             )
#             stdin, stdout, stderr = cl.exec_command(command, timeout=timeout)
#             output = stdout.read().decode('utf-8')
#             error = stderr.read().decode('utf-8')
#             if error:
#                 app_logger.error(f"Error executing command: {error}")
#             return output
#     except (paramiko.AuthenticationException, paramiko.SSHException, socket.error, Exception) as e:
#         app_logger.error(f"SSH command execution failed: {e}")
#         return None
#
#
# def generate_key(server_obj: Server) -> VPNKey:
#     """
#     Функция для генерации VPN ключа
#     :param server_obj: объект Server
#     :return: VPNKey
#     """
#     # Проверка, настроен ли севрер
#     try:
#         with paramiko.SSHClient() as cl:
#             cl.load_system_host_keys()
#             cl.set_missing_host_key_policy(paramiko.RejectPolicy())
#             cl.connect(
#                 hostname=server_obj.ip_address,
#                 username=server_obj.username,
#                 password=server_obj.password,
#                 look_for_keys=False,
#                 allow_agent=False,
#                 timeout=10
#             )
#             stdin, stdout, stderr = cl.exec_command(f"id {DEFAULT_SERVER_USER}", timeout=120)
#             output = stderr.read().decode('utf-8')
#             if "no such user" in output.lower():
#                 app_logger.warning(f"Сервер {server_obj.location} не настроен! Начинаю первичную настройку...")
#                 # Создаем нового пользователя
#                 stdin, stdout, stderr = cl.exec_command(f"useradd -m -s /bin/bash -G sudo "
#                                                         f"{DEFAULT_SERVER_USER}", timeout=20)
#                 print(stdout.read().decode('utf-8'))
#                 app_logger.info(f"Создан новый пользователь {DEFAULT_SERVER_USER} на сервере {server_obj.location}")
#
#                 # Устанавливаем пароль для нового пользователя
#                 p_obj = pxssh.pxssh()
#                 p_obj.login(server_obj.ip_address, server_obj.username, server_obj.password)
#                 p_obj.sendline(f"passwd {DEFAULT_SERVER_USER}")
#                 p_obj.expect('New password:')
#                 p_obj.sendline(DEFAULT_SERVER_PASSWORD)
#                 p_obj.expect('Retype new password:')
#                 p_obj.sendline(DEFAULT_SERVER_PASSWORD)
#                 p_obj.interact()
#                 p_obj.close()
#                 app_logger.info("Задан пароль для дефолтного пользователя.")
#
#             # Переключаемся на дефолтного пользователя
#             cl.exec_command(f"su - {DEFAULT_SERVER_USER}")
#
#             # Проверка
#             stdin, stdout, stderr = cl.exec_command(f"whoami")
#             app_logger.info(f"Переключились на пользователя {stdout.read().decode('utf-8')}")
#
#     except Exception as ex:
#         app_logger.error(f"Can't connect to server {server_obj.location}\n{ex}")
#         return None
#     # Базовая настройка сервера
#     print(execute_ssh_command(
#         ip=server_obj.ip_address,
#         username=server_obj.username,
#         password=server_obj.password,
#         command=basic_config_server_sh
#     ))
#
#     # Установка и настройка протокола xray
#     # print(execute_ssh_command(
#     #     ip=server_obj.ip_address,
#     #     username=DEFAULT_SERVER_USER,
#     #     password=DEFAULT_SERVER_PASSWORD,
#     #     command=test_script
#     # ))
#
#     # result_key = VPNKey.create(
#     #     server=server_obj,
#     #     name=f"VPN Key {server_obj.location} {len(server_obj.keys) + 1}",
#     #     key=f"{server_obj.location}_{server_obj.id} {len(server_obj.keys) + 1}",
#     #     qr_code=f"test path {len(server_obj.keys) + 1}",
#     #     is_valid=True
#     # )
#     # return result_key
#
#
# if __name__ == '__main__':
#     generate_key(Server.get_by_id(3))

import os
import json
import uuid
import tempfile
import paramiko
import qrcode
from pexpect import pxssh
from config_data.config import (
    DEFAULT_SERVER_USER,
    DEFAULT_SERVER_PASSWORD,
    XRAY_CONFIG_PATH,
    QR_CODE_DIR,
    XRAY_REALITY_SERVER_NAME,
    XRAY_REALITY_PUBLIC_KEY,
    XRAY_REALITY_SHORTID,
    XRAY_REALITY_FINGERPRINT
)
from loader import app_logger
from database.models import VPNKey, Server
import secrets
import random
import string
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization

# Функции для генерации параметров, если они не заданы

def generate_random_domain() -> str:
    """Генерирует случайный домен вида <8-символьная строка>.com."""
    return random.choice(["", "", ""])

def generate_public_key() -> str:
    """
    Генерирует пару ключей Ed25519 и возвращает публичный ключ в hex-формате.
    Приватный ключ нужно сохранить в безопасности (например, в защищённом хранилище) – здесь возвращается только публичная часть.
    """
    private_key = ed25519.Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    public_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw
    )
    return public_bytes.hex()

def generate_shortid() -> str:
    """Генерирует случайную шестизначную строку (6 hex символов)."""
    return secrets.token_hex(3)

def default_fingerprint() -> str:
    """Возвращает значение по умолчанию для TLS-фингерпринта."""
    return "chrome"

# Обновляем (если необходимо) глобальные параметры в конфиге.
# В продакшене рекомендуется сохранять их в надёжном хранилище, а не прямо в config.py.
def ensure_reality_params():
    from config_data import config  # Импортируем модуль конфигурации
    if not config.XRAY_REALITY_SERVER_NAME:
        config.XRAY_REALITY_SERVER_NAME = generate_random_domain()
        app_logger.info(f"Сгенерирован XRAY_REALITY_SERVER_NAME: {config.XRAY_REALITY_SERVER_NAME}")
    if not config.XRAY_REALITY_PUBLIC_KEY:
        config.XRAY_REALITY_PUBLIC_KEY = generate_public_key()
        app_logger.info(f"Сгенерирован XRAY_REALITY_PUBLIC_KEY: {config.XRAY_REALITY_PUBLIC_KEY}")
    if not config.XRAY_REALITY_SHORTID:
        config.XRAY_REALITY_SHORTID = generate_shortid()
        app_logger.info(f"Сгенерирован XRAY_REALITY_SHORTID: {config.XRAY_REALITY_SHORTID}")
    if not config.XRAY_REALITY_FINGERPRINT:
        config.XRAY_REALITY_FINGERPRINT = default_fingerprint()
        app_logger.info(f"Установлен XRAY_REALITY_FINGERPRINT: {config.XRAY_REALITY_FINGERPRINT}")

SECURE_XRAY_CONFIG = {
    "log": {
        "loglevel": "warning"
    },
    "inbounds": [
        {
            "port": 443,
            "protocol": "vless",
            "settings": {
                "clients": []
            },
            "streamSettings": {
                "network": "tcp",
                "security": "reality",
                "realitySettings": {
                    "show": False,
                    "dest": "127.0.0.1:80",
                    "xver": 1,
                    "serverName": XRAY_REALITY_SERVER_NAME,
                    "publicKey": XRAY_REALITY_PUBLIC_KEY,
                    "shortId": XRAY_REALITY_SHORTID,
                    "fingerprint": XRAY_REALITY_FINGERPRINT
                }
            }
        }
    ],
    "outbounds": [
        {
            "protocol": "freedom",
            "settings": {}
        }
    ]
}


def execute_ssh_command(ip: str, username: str, password: str, command: str, timeout: int = 60) -> str:
    """
    Выполняет SSH-команду на сервере и возвращает вывод.
    """
    try:
        with paramiko.SSHClient() as client:
            client.load_system_host_keys()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(hostname=ip, username=username, password=password, timeout=10)
            stdin, stdout, stderr = client.exec_command(command, timeout=timeout)
            output = stdout.read().decode('utf-8')
            return output.strip()
    except Exception as ex:
        app_logger.error(f"Ошибка при выполнении команды на {ip}: {ex}")
        return ""


def setup_server(server_obj: Server) -> bool:
    """
    Настраивает сервер для работы VPN.

    Алгоритм:
      1. Подключается по SSH к серверу (используя server_obj.username / password).
      2. Проверяет наличие дефолтного пользователя (DEFAULT_SERVER_USER). Если его нет, создаёт пользователя и задаёт пароль.
      3. С помощью SFTP загружает на сервер максимально защищённый конфиг Xray (с настройками Xray Reality).
      4. Перезапускает службу Xray.

    :param server_obj: объект Server с полями ip_address, username, password, location и т.д.
    :return: True, если настройка прошла успешно, иначе False.
    """
    try:
        # Подключаемся как администратор сервера
        with paramiko.SSHClient() as cl:
            cl.load_system_host_keys()
            cl.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            cl.connect(
                hostname=server_obj.ip_address,
                username=server_obj.username,
                password=server_obj.password,
                look_for_keys=False,
                allow_agent=False,
                timeout=10
            )
            # Проверяем наличие DEFAULT_SERVER_USER
            stdin, stdout, stderr = cl.exec_command(f"id {DEFAULT_SERVER_USER}", timeout=30)
            error_output = stderr.read().decode('utf-8')
            if "no such user" in error_output.lower():
                app_logger.info(
                    f"Пользователь {DEFAULT_SERVER_USER} не найден на сервере {server_obj.location}. Создаем его.")
                cl.exec_command(f"useradd -m -s /bin/bash -G sudo {DEFAULT_SERVER_USER}", timeout=20)
                # Устанавливаем пароль для нового пользователя через pxssh
                try:
                    p_obj = pxssh.pxssh(timeout=30)
                    p_obj.login(server_obj.ip_address, server_obj.username, server_obj.password)
                    p_obj.sendline(f"passwd {DEFAULT_SERVER_USER}")
                    p_obj.expect('New password:')
                    p_obj.sendline(DEFAULT_SERVER_PASSWORD)
                    p_obj.expect('Retype new password:')
                    p_obj.sendline(DEFAULT_SERVER_PASSWORD)
                    p_obj.prompt()
                    p_obj.logout()
                    app_logger.info(f"Пароль для {DEFAULT_SERVER_USER} успешно установлен.")
                except Exception as e:
                    app_logger.error(f"Ошибка при установке пароля для {DEFAULT_SERVER_USER}: {e}")
                    return False
        # Подключаемся для загрузки конфигурации Xray
        ssh = paramiko.SSHClient()
        ssh.load_system_host_keys()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(
            hostname=server_obj.ip_address,
            username=DEFAULT_SERVER_USER,
            password=DEFAULT_SERVER_PASSWORD,
            timeout=10
        )
        sftp = ssh.open_sftp()
        # Сохраняем локально наш безопасный конфиг
        local_config_path = os.path.join(tempfile.gettempdir(), f"secure_xray_config_{server_obj.id}.json")
        with open(local_config_path, "w") as f:
            json.dump(SECURE_XRAY_CONFIG, f, indent=2)
        # Загружаем файл на сервер
        sftp.put(local_config_path, XRAY_CONFIG_PATH)
        app_logger.info(f"Безопасный Xray конфиг загружен на сервер {server_obj.ip_address} по пути {XRAY_CONFIG_PATH}")
        sftp.close()
        ssh.close()
        # Перезапускаем службу Xray
        restart_output = execute_ssh_command(
            ip=server_obj.ip_address,
            username=DEFAULT_SERVER_USER,
            password=DEFAULT_SERVER_PASSWORD,
            command="systemctl restart xray",
            timeout=30
        )
        app_logger.info(f"Служба Xray перезапущена на сервере {server_obj.ip_address}. Вывод: {restart_output}")
        return True
    except Exception as ex:
        app_logger.error(f"Ошибка при настройке сервера {server_obj.location}: {ex}")
        return False


def generate_key(server_obj: Server) -> VPNKey | None:
    """
    Генерирует новый VPN ключ для сервера.

    Алгоритм:
      1. Генерируется уникальный UUID для нового клиента.
      2. Обновляется конфигурация Xray на сервере удалённо через утилиту jq:
         новый клиент добавляется в список inbound с протоколом "vless".
      3. Перезапускается служба Xray.
      4. На основе данных (новый UUID, ip_address и констант защиты) формируется VLESS‑ссылка.
      5. Генерируется QR‑код для VLESS‑ссылки, и путь к файлу записывается.
      6. Создаётся запись в модели VPNKey (peewee) и возвращается.

    :param server_obj: объект Server с полями ip_address, location, id, keys и т.д.
    :return: объект VPNKey с рабочей VLESS‑ссылкой и путем к QR‑коду, либо None при ошибке.
    """
    try:
        # Шаг 1. Генерация UUID для нового клиента
        client_uuid = str(uuid.uuid4())
        app_logger.info(f"Сгенерирован новый UUID для клиента: {client_uuid}")

        # Шаг 2. Обновление конфигурации Xray удалённо через утилиту jq.
        # Предполагается, что на сервере установлен jq.
        update_command = (
            f'jq \'.inbounds[0].settings.clients += [{{"id": "{client_uuid}", "flow": ""}}]\' {XRAY_CONFIG_PATH} '
            f'> {XRAY_CONFIG_PATH}.tmp && mv {XRAY_CONFIG_PATH}.tmp {XRAY_CONFIG_PATH}'
        )
        update_output = execute_ssh_command(
            ip=server_obj.ip_address,
            username=DEFAULT_SERVER_USER,
            password=DEFAULT_SERVER_PASSWORD,
            command=update_command,
            timeout=30
        )
        app_logger.info(f"Конфигурация Xray обновлена удалённо. Вывод: {update_output}")

        # Шаг 3. Перезапуск службы Xray для применения изменений.
        restart_output = execute_ssh_command(
            ip=server_obj.ip_address,
            username=DEFAULT_SERVER_USER,
            password=DEFAULT_SERVER_PASSWORD,
            command="systemctl restart xray",
            timeout=30
        )
        app_logger.info(f"Служба Xray перезапущена. Вывод: {restart_output}")

        # Шаг 4. Формирование VLESS-ссылки напрямую, без повторного скачивания конфига.
        # Ссылка формируется с использованием параметров защиты Xray Reality.
        vless_link = (
            f"vless://{client_uuid}@{server_obj.ip_address}:443?"
            f"encryption=none&security=reality&fp={XRAY_REALITY_FINGERPRINT}&"
            f"sni={XRAY_REALITY_SERVER_NAME}&pbk={XRAY_REALITY_PUBLIC_KEY}&sid={XRAY_REALITY_SHORTID}"
        )
        app_logger.info(f"Сформирована VLESS ссылка: {vless_link}")

        # Шаг 5. Генерация QR-кода для VLESS ссылки.
        key_number = len(server_obj.keys) + 1 if hasattr(server_obj, "keys") else 1
        qr_code_filename = f"vpn_key_{server_obj.id}_{key_number}.png"
        qr_code_path = os.path.join(QR_CODE_DIR, qr_code_filename)
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=10,
            border=4
        )
        qr.add_data(vless_link)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        img.save(qr_code_path)
        app_logger.info(f"QR-код сгенерирован и сохранён по пути: {qr_code_path}")

        # Шаг 6. Создание записи VPNKey в БД с использованием peewee.
        vpn_key = VPNKey.create(
            server=server_obj,
            name=f"VPN Key {server_obj.location} #{key_number}",
            key=vless_link,
            qr_code=qr_code_path,
            is_valid=True
        )
        app_logger.info(f"VPN ключ успешно создан: {vpn_key.key}")
        return vpn_key

    except Exception as ex:
        app_logger.error(f"Ошибка при генерации VPN ключа для сервера {server_obj.location}: {ex}")
        return None