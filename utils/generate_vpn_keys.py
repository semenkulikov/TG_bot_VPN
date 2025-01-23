import socket
from typing import Optional
import paramiko
from database.models import VPNKey, Server
import os
from config_data.config import BASE_DIR
from loader import app_logger


script_text = """
echo 'Hello, world!'
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
    result_key = VPNKey.create(
        server=server_obj,
        name=f"VPN Key {server_obj.location} {len(server_obj.keys) + 1}",
        key=f"{server_obj.location}_{server_obj.id} {len(server_obj.keys) + 1}",
        qr_code=f"test path {len(server_obj.keys) + 1}",
        is_valid=True
    )
    return result_key


