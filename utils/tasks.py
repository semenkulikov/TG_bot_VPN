import datetime

from apscheduler.schedulers.background import BackgroundScheduler

from keyboards.inline.subscribed import get_renew_markup_for_user
from loader import bot, app_logger
from database.models import VPNKey, User, UserVPNKey
from config_data.config import CHANNEL_ID, ALLOWED_USERS
from utils.functions import is_subscribed
from utils.work_vpn_keys import revoke_key

# Глобальный словарь для хранения job_id запланированных задач по отзыву ключей
pending_revocation_jobs = {}


def check_and_revoke_keys():
    """
    Проверяет, подписаны ли пользователи, и отзывает все VPN ключи у тех, кто отписался.
    """
    app_logger.info("Проверка пользователей...")

    # Перебираем всех пользователей
    for user in User.select():
        if is_subscribed(CHANNEL_ID, user.user_id):
            user.is_subscribed = True
            user.save()
        else:
            user.is_subscribed = False
            app_logger.info(f"Пользователь {user.full_name} не подписан на канал.")
            # Перебираем все VPN ключи, связанные с этим пользователем (через связь many-to-many)
            for uv in list(user.vpn_keys):
                vpn_key = uv.vpn_key
                try:
                    bot.send_message(
                        user.user_id,
                        f"🚫 Ваш VPN ключ «{vpn_key.name}» был отозван, так как вы отписались от канала."
                    )
                    app_logger.info(f"У пользователя {user.full_name} ключ {vpn_key.name} отозван.")
                except Exception as e:
                    app_logger.error(f"Не удалось отправить уведомление пользователю {user.user_id}: {e}")
                # Отзываем ключ (функция revoke_key должна выполнять отзыв ключа)
                if revoke_key(vpn_key):
                    app_logger.info(f"VPN ключ {vpn_key.id} успешно отозван.")
                else:
                    app_logger.error(f"Ошибка при отзыве ключа {vpn_key.id}.")
            # Удаляем все связи между пользователем и его VPN ключами
            UserVPNKey.delete().where(UserVPNKey.user == user).execute()
            user.save()


def schedule_key_revocation_for_user(user_obj: User, scheduler: BackgroundScheduler):
    """
    Планирует задачу отзыва всех VPN ключей пользователя через 1 час.
    Сохраняет идентификатор задачи в глобальном словаре по user_obj.user_id.
    """
    def revoke_job():
        try:
            # Отправляем уведомление пользователю о том, что его ключи аннулированы
            bot.send_message(
                user_obj.user_id,
                f"⌛ Время продления VPN ключей истекло! Все ваши VPN ключи аннулированы.\n"
                "Чтобы продолжить пользоваться сервисом, создайте новый ключ."
            )
        except Exception as e:
            app_logger.error(f"Ошибка отправки уведомления пользователю {user_obj.user_id}: {e}")
        # Отзываем все ключи, привязанные к пользователю
        for uv in list(user_obj.vpn_keys):
            vpn_key = uv.vpn_key
            if revoke_key(vpn_key):
                app_logger.info(f"VPN ключ {vpn_key.name} аннулирован по истечении времени "
                                f"продления для пользователя {user_obj.user_id}.")
            else:
                app_logger.error(f"Ошибка при отзыве VPN ключа {vpn_key.name} для пользователя {user_obj.user_id}.")
        # Удаляем все записи из таблицы связи для данного пользователя
        UserVPNKey.delete().where(UserVPNKey.user == user_obj).execute()
        pending_revocation_jobs.pop(user_obj.user_id, None)

    # Планируем выполнение через 1 час
    run_time = datetime.datetime.now() + datetime.timedelta(hours=1)
    job = scheduler.add_job(revoke_job, 'date', run_date=run_time)
    pending_revocation_jobs[user_obj.user_id] = job.id
    app_logger.info(f"Запланирована задача отзыва для пользователя {user_obj.full_name} "
                    f"(ID: {user_obj.user_id}) через 1 час.")

def cancel_key_revocation_for_user(user_obj: User, scheduler: BackgroundScheduler):
    """
    Отменяет запланированную задачу отзыва VPN ключей для пользователя, если она существует.
    """
    job_id = pending_revocation_jobs.pop(user_obj.user_id, None)
    if job_id:
        scheduler.remove_job(job_id)
        app_logger.info(f"Запланированная задача отзыва для пользователя {user_obj.full_name} отменена.")


def send_renewal_notifications(scheduler: BackgroundScheduler):
    """
    Каждые 8 часов рассылает пользователям уведомления о продлении VPN ключей.
    Для каждого пользователя, у которого есть хотя бы один активный VPN ключ, отправляется сообщение с inline‑кнопкой.
    При отправке планируется задача, которая через 1 час отзовет все ключи, если пользователь не нажмёт кнопку.
    """
    app_logger.info("Отправка уведомлений о продлении VPN ключей...")
    # Перебираем всех пользователей, у которых есть хотя бы один ключ в связи
    for user in User.select():
        # Если у пользователя есть VPN ключи (через связь many-to-many)
        if user.vpn_keys.count() > 0:
            try:
                bot.send_message(
                    user.user_id,
                    f"⏰ Напоминаем, что срок действия ваших VPN ключей скоро истечёт.\n"
                    "Нажмите кнопку ниже, чтобы продлить их действие.",
                    reply_markup=get_renew_markup_for_user(user.user_id)
                )
                # Планируем задачу отзыва для этого пользователя через 1 час
                schedule_key_revocation_for_user(user, scheduler)
            except Exception as e:
                app_logger.error(f"Ошибка отправки уведомления пользователю {user.user_id}: {e}")
