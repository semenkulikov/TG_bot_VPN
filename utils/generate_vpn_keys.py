from database.models import VPNKey, Server
import os
from config_data.config import BASE_DIR


script_text = """

"""

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


