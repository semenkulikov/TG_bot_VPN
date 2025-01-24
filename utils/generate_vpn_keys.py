import socket
from typing import Optional
import paramiko
import pexpect
from pexpect import pxssh
from database.models import VPNKey, Server
import os
from config_data.config import BASE_DIR, DEFAULT_SERVER_USER, DEFAULT_SERVER_PASSWORD
from loader import app_logger


basic_config_server_sh = """
# echo 'Hello, world!' && whoami &&
sudo apt install jq openssl &&
curl -L https://codeload.github.com/EvgenyNerush/easy-xray/tar.gz/main | tar -xz &&
cd easy-xray-main &&
chmod +x ex.sh &&
sudo ./ex.sh install &&
sudo ./ex.sh conf
"""


user_settings = f"""
sudo useradd -m -s /bin/bash -G sudo {DEFAULT_SERVER_USER} &&
passwd {DEFAULT_SERVER_USER}
"""

test_script = """
"""


def execute_ssh_command(
    ip: str,
    username: str,
    password: str,
    command: str,
    timeout: int = 120
) -> Optional[str]:
    try:
        with paramiko.SSHClient() as cl:
            cl.load_system_host_keys()
            cl.set_missing_host_key_policy(paramiko.RejectPolicy())
            cl.connect(
                hostname=ip,
                username=username,
                password=password,
                look_for_keys=False,
                allow_agent=False,
                timeout=10
            )
            stdin, stdout, stderr = cl.exec_command(command, timeout=timeout)
            output = stdout.read().decode('utf-8')
            error = stderr.read().decode('utf-8')
            if error:
                app_logger.error(f"Error executing command: {error}")
            return output
    except (paramiko.AuthenticationException, paramiko.SSHException, socket.error, Exception) as e:
        app_logger.error(f"SSH command execution failed: {e}")
        return None


def generate_key(server_obj: Server) -> VPNKey:
    """
    Функция для генерации VPN ключа
    :param server_obj: объект Server
    :return: VPNKey
    """
    # Проверка, настроен ли севрер
    try:
        with paramiko.SSHClient() as cl:
            cl.load_system_host_keys()
            cl.set_missing_host_key_policy(paramiko.RejectPolicy())
            cl.connect(
                hostname=server_obj.ip_address,
                username=server_obj.username,
                password=server_obj.password,
                look_for_keys=False,
                allow_agent=False,
                timeout=10
            )
            stdin, stdout, stderr = cl.exec_command(f"id {DEFAULT_SERVER_USER}", timeout=120)
            output = stderr.read().decode('utf-8')
            if "no such user" in output.lower():
                app_logger.warning(f"Сервер {server_obj.location} не настроен! Начинаю первичную настройку...")
                # Создаем нового пользователя
                stdin, stdout, stderr = cl.exec_command(f"useradd -m -s /bin/bash -G sudo "
                                                        f"{DEFAULT_SERVER_USER}", timeout=20)
                print(stdout.read().decode('utf-8'))
                app_logger.info(f"Создан новый пользователь {DEFAULT_SERVER_USER} на сервере {server_obj.location}")

                # Устанавливаем пароль для нового пользователя
                p_obj = pxssh.pxssh()
                p_obj.login(server_obj.ip_address, server_obj.username, server_obj.password)
                p_obj.sendline(f"passwd {DEFAULT_SERVER_USER}")
                p_obj.expect('New password:')
                p_obj.sendline(DEFAULT_SERVER_PASSWORD)
                p_obj.expect('Retype new password:')
                p_obj.sendline(DEFAULT_SERVER_PASSWORD)
                p_obj.interact()
                p_obj.close()
                app_logger.info("Задан пароль для дефолтного пользователя.")

            # Переключаемся на дефолтного пользователя
            cl.exec_command(f"su - {DEFAULT_SERVER_USER}")

            # Проверка
            stdin, stdout, stderr = cl.exec_command(f"whoami")
            app_logger.info(f"Переключились на пользователя {stdout.read().decode('utf-8')}")

    except Exception as ex:
        app_logger.error(f"Can't connect to server {server_obj.location}\n{ex}")
        return None
    # Базовая настройка сервера
    print(execute_ssh_command(
        ip=server_obj.ip_address,
        username=server_obj.username,
        password=server_obj.password,
        command=basic_config_server_sh
    ))

    # Установка и настройка протокола xray
    # print(execute_ssh_command(
    #     ip=server_obj.ip_address,
    #     username=DEFAULT_SERVER_USER,
    #     password=DEFAULT_SERVER_PASSWORD,
    #     command=test_script
    # ))

    # result_key = VPNKey.create(
    #     server=server_obj,
    #     name=f"VPN Key {server_obj.location} {len(server_obj.keys) + 1}",
    #     key=f"{server_obj.location}_{server_obj.id} {len(server_obj.keys) + 1}",
    #     qr_code=f"test path {len(server_obj.keys) + 1}",
    #     is_valid=True
    # )
    # return result_key


if __name__ == '__main__':
    generate_key(Server.get_by_id(3))