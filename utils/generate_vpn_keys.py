import base64
import os
import json
import uuid
import tempfile
import paramiko
import qrcode
import secrets
import random
from cryptography.hazmat.primitives.asymmetric import x25519
from cryptography.hazmat.primitives import serialization
from loader import app_logger
from database.models import VPNKey, Server
import copy
from config_data.config import (
    DEFAULT_SERVER_USER,
    DEFAULT_SERVER_PASSWORD,
    XRAY_CONFIG_PATH,
    QR_CODE_DIR,
    XRAY_REALITY_FINGERPRINT,
    DOMAINS_LIST,
)

def generate_x25519_keys_base64() -> dict:
    """
    Генерирует пару ключей X25519 и возвращает их в base64-формате,
    что соответствует требованиям Xray Reality.
    """
    private_key = x25519.X25519PrivateKey.generate()
    public_key = private_key.public_key()
    private_bytes = private_key.private_bytes(
         encoding=serialization.Encoding.Raw,
         format=serialization.PrivateFormat.Raw,
         encryption_algorithm=serialization.NoEncryption()
    )
    public_bytes = public_key.public_bytes(
         encoding=serialization.Encoding.Raw,
         format=serialization.PublicFormat.Raw
    )
    private_b64 = base64.b64encode(private_bytes).decode('utf-8')
    public_b64 = base64.b64encode(public_bytes).decode('utf-8')
    return {"private": private_b64, "public": public_b64}


def remote_generate_xray_keys(server_obj: Server) -> dict:
    cmd = "xray x25519"
    output = execute_ssh_command(
        ip=server_obj.ip_address,
        username=DEFAULT_SERVER_USER,
        password=DEFAULT_SERVER_PASSWORD,
        command=cmd,
        timeout=30
    )
    keys = {}
    for line in output.splitlines():
        if line.lower().startswith("private"):
            keys["private"] = line.split(":", 1)[1].strip()
        elif line.lower().startswith("public"):
            keys["public"] = line.split(":", 1)[1].strip()
    if "private" in keys and "public" in keys:
        return keys
    else:
        app_logger.error("Не удалось сгенерировать ключи через 'xray x25519' на сервере.")
        return None


def ensure_reality_params(config_template: dict, server_obj: Server) -> tuple:
    # Выбираем случайный домен из DOMAINS_LIST
    domain = random.choice(DOMAINS_LIST)
    # Генерируем ключи (приватный и публичный) на сервере
    keys = remote_generate_xray_keys(server_obj)
    if not keys:
        raise Exception("Удаленная генерация ключей не удалась")
    # Генерируем список shortIds (например, 6 значений)
    short_ids = [secrets.token_hex(4) for _ in range(6)]

    # Создаем глубокую копию шаблона, чтобы не изменять оригинал
    config = copy.deepcopy(config_template)

    # Обновляем параметры в секции realitySettings
    reality = config["inbounds"][0]["streamSettings"]["realitySettings"]
    reality["dest"] = f"{domain}:443"
    reality["serverNames"] = [domain]
    reality["privateKey"] = keys["private"]
    reality["publicKey"] = keys["public"]    # <-- Добавляем поле publicKey
    reality["shortIds"] = short_ids

    # Обновляем домены в routing.rules (если указаны)
    for rule in config.get("routing", {}).get("rules", []):
        if "domain" in rule:
            rule["domain"] = [domain]

    # Возвращаем обновленный конфиг и публичный ключ для формирования VLESS-ссылки
    return config, keys["public"]


SECURE_XRAY_CONFIG = {
    "log": {
        "loglevel": "debug"
    },
    "inbounds": [
        {
            "listen": "0.0.0.0",
            "port": 443,
            "protocol": "vless",
            "settings": {
                "clients": [],
                "decryption": "none"
            },
            "streamSettings": {
                "network": "tcp",
                "security": "reality",
                "realitySettings": {
                    "dest": "",
                    "serverNames": [],
                    "privateKey": "",
                    "shortIds": [],
                    "publicKey": ""
                }
            },
            "sniffing": {
                "enabled": True,
                "destOverride": ["http", "tls", "quic"]
            }
        }
    ],
    "outbounds": [
        {
            "protocol": "freedom",
            "tag": "direct"
        },
        {
            "protocol": "blackhole",
            "tag": "block"
        }
    ]
}


def execute_ssh_command(ip: str, username: str, password: str, command: str, timeout: int = 60) -> str:
    client = paramiko.SSHClient()
    try:
        client.load_system_host_keys()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(
            hostname=ip,
            username=username,
            password=password,
            timeout=10,
            allow_agent=False,
            look_for_keys=False
        )
        stdin, stdout, stderr = client.exec_command(command, timeout=timeout, get_pty=True)
        output = stdout.read().decode('utf-8').strip()
        err = stderr.read().decode('utf-8').strip()
        if err:
            app_logger.error(f"Ошибка выполнения команды на {ip}: {err}")
        return output
    except Exception as ex:
        app_logger.error(f"Ошибка при подключении к {ip}: {ex}")
        return ""
    finally:
        client.close()




def setup_server(server_obj: Server) -> bool:
    """
    Настраивает сервер для работы VPN.
    Если возникают какие-то ошибки при установке пакетов -
    https://timeweb.cloud/docs/unix-guides/troubleshooting-unix/ustranenie-oshibki-could-not-get-lock-var-lib-dpkg-lock

    Алгоритм:
      1. Подключение по SSH с правами администратора.
      2. Проверка наличия DEFAULT_SERVER_USER. Если отсутствует, создаём пользователя и устанавливаем пароль.
         Для установки пароля используется команда chpasswd, что исключает необходимость интерактивного ввода.
      3. С использованием SFTP загружается обновлённый и безопасный конфиг Xray.
      4. Перезапуск службы Xray.

    :param server_obj: объект Server с данными для подключения.
    :return: True, если настройка прошла успешно, иначе False.
    """
    try:
        # Подключаемся к серверу под администратором
        with paramiko.SSHClient() as ssh_admin:
            ssh_admin.load_system_host_keys()
            ssh_admin.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh_admin.connect(
                hostname=server_obj.ip_address,
                username=server_obj.username,
                password=server_obj.password,
                timeout=10,
                allow_agent=False,
                look_for_keys=False
            )
            # Проверяем наличие пользователя DEFAULT_SERVER_USER
            check_cmd = f"id {DEFAULT_SERVER_USER}"
            stdin, stdout, stderr = ssh_admin.exec_command(check_cmd, timeout=30)
            error_output = stderr.read().decode('utf-8').lower()
            if "no such user" in error_output:
                app_logger.info(
                    f"Пользователь {DEFAULT_SERVER_USER} не найден на сервере {server_obj.location}. Создаем его.")
                # Создаем пользователя
                ssh_admin.exec_command(f"useradd -m -s /bin/bash -G sudo {DEFAULT_SERVER_USER}", timeout=20)
                # Устанавливаем пароль с помощью chpasswd (без интерактивного ввода)
                passwd_cmd = f'echo "{DEFAULT_SERVER_USER}:{DEFAULT_SERVER_PASSWORD}" | chpasswd'
                ssh_admin.exec_command(passwd_cmd, timeout=20)
                app_logger.info(f"Пользователь {DEFAULT_SERVER_USER} создан и пароль установлен.")
            else:
                app_logger.info(f"Пользователь {DEFAULT_SERVER_USER} уже существует")
        update_jq_cmd = (
            f"echo {DEFAULT_SERVER_PASSWORD} | sudo -S apt update && "
            f"echo {DEFAULT_SERVER_PASSWORD} | sudo -S apt upgrade -y && "
            f"echo {DEFAULT_SERVER_PASSWORD} | sudo -S apt install -y jq"
        )
        execute_ssh_command(
            ip=server_obj.ip_address,
            username=DEFAULT_SERVER_USER,
            password=DEFAULT_SERVER_PASSWORD,
            command=update_jq_cmd,
            timeout=300
        )
        app_logger.info(f"Системные компоненты обновлены, зависимости установлены.")
        xray_check_cmd = "which xray"
        xray_installed = execute_ssh_command(
            ip=server_obj.ip_address,
            username=DEFAULT_SERVER_USER,
            password=DEFAULT_SERVER_PASSWORD,
            command=xray_check_cmd,
            timeout=30
        )
        if not xray_installed:
            app_logger.info("Xray не найден, начинаю установку с использованием официального скрипта.")
            install_xray_cmd = (
                "curl -O https://raw.githubusercontent.com/XTLS/Xray-install/main/install-release.sh && "
                f"echo {DEFAULT_SERVER_PASSWORD} | sudo -S bash install-release.sh"
            )
            output_install_xray = execute_ssh_command(
                ip=server_obj.ip_address,
                username=DEFAULT_SERVER_USER,
                password=DEFAULT_SERVER_PASSWORD,
                command=install_xray_cmd,
                timeout=300
            )
            app_logger.info(f"Установка Xray выполнена успешно. Вывод: {output_install_xray}")
        else:
            app_logger.info("Xray уже установлен. Сервер настроен")
            return True

        # Разрешаем 443 порт
        allow_443_port_command = (
            f"echo {DEFAULT_SERVER_PASSWORD} | sudo -S ufw allow 443/tcp && "
            f"echo {DEFAULT_SERVER_PASSWORD} | sudo -S netstat -tulpn | grep ':443'"
        )
        port_output = execute_ssh_command(
            ip=server_obj.ip_address,
            username=DEFAULT_SERVER_USER,
            password=DEFAULT_SERVER_PASSWORD,
            command=allow_443_port_command,
            timeout=300
        )
        app_logger.info(f"Порт 443 разрешен. Проверка: {port_output}")
        # Подключаемся для загрузки конфигурации Xray
        ssh = paramiko.SSHClient()
        ssh.load_system_host_keys()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(
            hostname=server_obj.ip_address,
            username=DEFAULT_SERVER_USER,
            password=DEFAULT_SERVER_PASSWORD,
            timeout=10,
            allow_agent=False,
            look_for_keys=False
        )
        sftp = ssh.open_sftp()

        # заполняем конфигурацию данными
        final_config, public_key = ensure_reality_params(SECURE_XRAY_CONFIG, server_obj)

        # Сохраняем public key в модель сервера
        server_obj.public_key = public_key
        server_obj.save()

        # Сохраняем локально безопасный конфиг Xray
        local_config_path = os.path.join(tempfile.gettempdir(), f"secure_xray_config_{server_obj.id}.json")
        with open(local_config_path, "w") as f:
            json.dump(final_config, f, indent=2)
        # Загружаем конфиг на сервер

        temp_remote_path = f"/tmp/secure_xray_config_{server_obj.id}.json"
        sftp.put(local_config_path, temp_remote_path)
        app_logger.info(f"Конфигурационный файл загружен во временную директорию: {temp_remote_path}")

        # Перемещаем файл с помощью sudo, чтобы обойти ограничение прав доступа.
        move_cmd = f'echo {DEFAULT_SERVER_PASSWORD} | sudo -S mv {temp_remote_path} {XRAY_CONFIG_PATH}'
        move_output = execute_ssh_command(
            ip=server_obj.ip_address,
            username=DEFAULT_SERVER_USER,
            password=DEFAULT_SERVER_PASSWORD,
            command=move_cmd,
            timeout=30
        )
        app_logger.info(f"Файл конфигурации перемещён в {XRAY_CONFIG_PATH}. Вывод: {move_output}")
        sftp.close()
        ssh.close()

        # Проверяем конфиг файл на валидность
        test_config = f'echo {DEFAULT_SERVER_PASSWORD} | sudo -S xray run -test -confdir /usr/local/etc/xray/'
        test_output = execute_ssh_command(
            ip=server_obj.ip_address,
            username=DEFAULT_SERVER_USER,
            password=DEFAULT_SERVER_PASSWORD,
            command=test_config,
            timeout=30
        )
        app_logger.info(f"Конфиг проверен. Вывод: {test_output}")

        # Синхронизируем время на сервере
        time_syn_cmd = f'echo {DEFAULT_SERVER_PASSWORD} | sudo -S timedatectl set-ntp true'
        execute_ssh_command(
            ip=server_obj.ip_address,
            username=DEFAULT_SERVER_USER,
            password=DEFAULT_SERVER_PASSWORD,
            command=time_syn_cmd,
            timeout=30
        )
        app_logger.info(f"Время на сервере синхронизировано.")

        # Перезапускаем службу Xray для применения конфигурации
        restart_cmd = f'echo {DEFAULT_SERVER_PASSWORD} | sudo -S systemctl restart xray'
        restart_output = execute_ssh_command(
            ip=server_obj.ip_address,
            username=DEFAULT_SERVER_USER,
            password=DEFAULT_SERVER_PASSWORD,
            command=restart_cmd,
            timeout=30
        )
        app_logger.info(f"Служба Xray перезапущена. Вывод: {restart_output}")
        return True
    except Exception as ex:
        app_logger.error(f"Ошибка при настройке сервера {server_obj.location}: {ex}")
        return False


def generate_key(server_obj: Server) -> VPNKey | None:
    """
    Генерирует новый VPN ключ для сервера.

    Алгоритм:
      1. Генерация уникального UUID для клиента.
      2. Обновление конфигурации Xray на сервере с помощью утилиты jq (добавление нового клиента в список).
      3. Перезапуск службы Xray.
      4. Формирование VLESS-ссылки с параметрами Xray Reality.
      5. Генерация QR-кода для VLESS-ссылки.
      6. Создание записи VPNKey в базе данных.

    :param server_obj: объект Server.
    :return: объект VPNKey с рабочей VLESS‑ссылкой и путем к QR‑коду, либо None при ошибке.
    """
    try:
        # Шаг 1. Генерация UUID для нового клиента
        client_uuid = str(uuid.uuid4())
        app_logger.info(f"Сгенерирован новый UUID для клиента: {client_uuid}")

        # Шаг 2. Обновление конфигурации Xray через jq
        update_cmd = (
            f'echo {DEFAULT_SERVER_PASSWORD} | sudo -S sh -c '
            f'"jq \'.inbounds[0].settings.clients += [{{\\"id\\": \\"{client_uuid}\\", '
            f'\\"flow\\": \\"xtls-rprx-vision\\"}}]\' {XRAY_CONFIG_PATH} > {XRAY_CONFIG_PATH}.tmp && '
            f'mv {XRAY_CONFIG_PATH}.tmp {XRAY_CONFIG_PATH}"'
        )
        update_output = execute_ssh_command(
            ip=server_obj.ip_address,
            username=DEFAULT_SERVER_USER,
            password=DEFAULT_SERVER_PASSWORD,
            command=update_cmd,
            timeout=30
        )
        app_logger.info(f"Конфигурация Xray обновлена. Вывод: {update_output}")

        # Шаг 3. Перезапуск службы Xray
        restart_cmd = f'echo {DEFAULT_SERVER_PASSWORD} | sudo -S systemctl restart xray'
        restart_output = execute_ssh_command(
            ip=server_obj.ip_address,
            username=DEFAULT_SERVER_USER,
            password=DEFAULT_SERVER_PASSWORD,
            command=restart_cmd,
            timeout=30
        )
        app_logger.info(f"Служба Xray перезапущена. Вывод: {restart_output}")

        # Шаг 4. Формирование VLESS-ссылки
        # Получаем данные из конфиг файла
        config_content = execute_ssh_command(
            ip=server_obj.ip_address,
            username=DEFAULT_SERVER_USER,
            password=DEFAULT_SERVER_PASSWORD,
            command=f"cat {XRAY_CONFIG_PATH}",
            timeout=30
        )
        try:
            config_json = json.loads(config_content)
            # Извлекаем данные из секции realitySettings во втором inbound (индекс 1)
            reality_settings = config_json["inbounds"][0]["streamSettings"]["realitySettings"]
            # Предполагаем, что в конфиге теперь есть оба параметра: publicKey и serverNames
            server_name = reality_settings.get("serverNames", [None])[0]
            public_key = server_obj.public_key
            short_id = random.choice(reality_settings["shortIds"])
            if not server_name or not public_key or not short_id:
                raise ValueError("Недостаточно параметров Xray Reality в конфиге.")
        except Exception as e:
            app_logger.error(f"Ошибка при парсинге конфигурационного файла: {e}")
            return None

        vless_link = (
            f"vless://{client_uuid}@{server_obj.ip_address}:443?"
            f"security=reality&"
            f"encryption=none&"
            f"flow=xtls-rprx-vision&"
            f"type=tcp&"
            f"fp={XRAY_REALITY_FINGERPRINT}&"
            f"sni={server_name}&"
            f"pbk={public_key}&"
            f"sid={short_id}#GuardVPN"
        )
        app_logger.info(f"Сформирована VLESS ссылка: {vless_link}")


        # Шаг 5. Генерация QR-кода
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
