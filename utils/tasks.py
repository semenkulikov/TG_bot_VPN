import datetime

from apscheduler.schedulers.background import BackgroundScheduler

from keyboards.inline.subscribed import get_renew_markup
from loader import bot, app_logger
from database.models import VPNKey, User
from config_data.config import CHANNEL_ID, ALLOWED_USERS
from utils.functions import is_subscribed
from utils.work_vpn_keys import revoke_key

# Глобальный словарь для хранения job_id запланированных задач по отзыву ключей
pending_revocation_jobs = {}


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
                user.vpn_key = None
                user.save()
                try:
                    bot.send_message(user.user_id,
                        "Ваш VPN ключ отозван, так как вы отписались от канала.")
                    app_logger.info(f"Пользователь {user.full_name} отписался от канала, "
                                    f"поэтому его ключ {vpn_key.name} был отозван!")
                    # for admin_id in ALLOWED_USERS:
                    #     bot.send_message(admin_id,
                    #         f"Пользователь {user.full_name} отписался от канала, "
                    #                 f"поэтому его ключ {vpn_key.name} был отозван!")
                except Exception as e:
                    app_logger.error(f"Не удалось отправить уведомление пользователю {user.user_id}: {e}")
                revoke_this = True
        if revoke_this:
            if revoke_key(vpn_key):
                app_logger.info(f"VPN ключ {vpn_key.id} отозван из-за отписки пользователя(ей).")
            else:
                app_logger.error(f"Ошибка при отзыве ключа {vpn_key.id}.")


def schedule_key_revocation(vpn_key: VPNKey, user_obj: User, scheduler: BackgroundScheduler):
    """
    Планирует задачу отзыва ключа через 1 час.
    Сохраняет идентификатор задачи в глобальном словаре по vpn_key.id.
    """
    def revoke_job():
        # Если задача не была отменена (то есть пользователь не продлил ключ)
        if vpn_key.id in pending_revocation_jobs:
            try:
                bot.send_message(
                    user_obj.user_id,
                    f"⌛ Время продления VPN ключа «{vpn_key.name}» истекло! Ключ был аннулирован.\n"
                    f"Вы можете создать новый ключ, нажав на кнопку Серверы 👇"
                )
            except Exception as e:
                app_logger.error(f"Ошибка отправки уведомления пользователю {user_obj.full_name}: {e}")
            revoke_key(vpn_key)
            user_obj.vpn_key = None
            user_obj.save()
            app_logger.info(f"VPN ключ {vpn_key.name} аннулирован по истечении времени продления!")
            # Убираем задачу из pending_revocation_jobs
            pending_revocation_jobs.pop(vpn_key.id, None)

    # Планируем выполнение через 1 час
    job = scheduler.add_job(revoke_job, 'date', run_date=datetime.datetime.now() + datetime.timedelta(hours=1))
    pending_revocation_jobs[vpn_key.id] = job.id
    app_logger.info(f"Запланирована задача отзыва для ключа {vpn_key.name} через 1 час.")

def cancel_key_revocation(vpn_key: VPNKey, scheduler: BackgroundScheduler):
    """
    Отменяет запланированную задачу отзыва ключа, если она существует.
    """
    job_id = pending_revocation_jobs.pop(vpn_key.id, None)
    if job_id:
        scheduler.remove_job(job_id)
        app_logger.info(f"Запланированная задача отзыва для ключа {vpn_key.name} отменена.")


def send_renewal_notifications(scheduler: BackgroundScheduler):
    """
    Каждые 8 часов рассылает пользователям уведомления о продлении VPN ключей.
    Для каждого активного (зарезервированного) ключа отправляется сообщение с inline-кнопкой.
    При отправке планируется задача, которая через 1 час отзовет ключ, если пользователь не нажмёт кнопку.
    """
    # Получаем список пользователей, у которых назначен VPN ключ (предполагается, что у пользователя есть vpn_key)
    app_logger.info("Отправка уведомлений о продлении VPN ключей...")

    for user in User.select().where(User.vpn_key.is_null(False)):
        vpn_key = user.vpn_key
        try:
            bot.send_message(
                user.user_id,
                f"⏰ Напоминаем, что срок действия вашего VPN ключа «{vpn_key.name}» скоро истечёт.\n"
                "Нажмите кнопку ниже, чтобы продлить его действие.",
                reply_markup=get_renew_markup(vpn_key.id)
            )
            # Планируем задачу отзыва ключа через 1 час
            schedule_key_revocation(vpn_key, user, scheduler)
        except Exception as e:
            app_logger.error(f"Ошибка отправки уведомления пользователю {user.user_id}: {e}")
