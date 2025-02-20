from loader import bot, app_logger
from database.models import VPNKey
from config_data.config import CHANNEL_ID, ALLOWED_USERS
from utils.functions import is_subscribed
from utils.work_vpn_keys import revoke_key


def check_and_revoke_keys():
    """
    Проверяет, подписаны ли пользователи, которым выданы VPN ключи.
    Если обнаруживается, что хотя бы один пользователь, привязанный к ключу, отписался,
    отправляет ему уведомление и отзывает ключ.
    """
    # Получаем активные ключи
    app_logger.info("Проверка пользователей...")

    active_keys = VPNKey.select().where(VPNKey.is_valid == False)
    for vpn_key in active_keys:
        revoke_this = False
        for user in vpn_key.users:
            # Если пользователь не подписан, отправляем уведомление
            if not is_subscribed(CHANNEL_ID, user.user_id):
                user.is_subscribed = False
                user.save()
                try:
                    bot.send_message(user.user_id,
                        "Ваш VPN ключ отозван, так как вы отписались от канала.")
                    app_logger.info(f"Пользователь {user.full_name} отписался от канала, "
                                    f"поэтому его ключ {vpn_key.name} был отозван!")
                    for admin_id in ALLOWED_USERS:
                        bot.send_message(admin_id,
                            f"Пользователь {user.full_name} отписался от канала, "
                                    f"поэтому его ключ {vpn_key.name} был отозван!")
                except Exception as e:
                    app_logger.error(f"Не удалось отправить уведомление пользователю {user.user_id}: {e}")
                revoke_this = True
        if revoke_this:
            if revoke_key(vpn_key):
                app_logger.info(f"VPN ключ {vpn_key.id} отозван из-за отписки пользователя(ей).")
            else:
                app_logger.error(f"Ошибка при отзыве ключа {vpn_key.id}.")
