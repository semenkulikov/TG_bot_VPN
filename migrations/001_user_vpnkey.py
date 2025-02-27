# migrations/001_user_vpnkey.py
import peewee
from playhouse.migrate import SqliteMigrator, migrate
from database.models import db, User, VPNKey, UserVPNKey
from loader import app_logger


def run_migration():
    migrator = SqliteMigrator(db)

    # 1. Создаем новую таблицу UserVPNKey, если её ещё нет
    if not UserVPNKey.table_exists():
        UserVPNKey.create_table()
        app_logger.debug("Таблица UserVPNKey создана.")
    else:
        app_logger.debug("Таблица UserVPNKey уже существует.")

    # 2. Если раньше у пользователей было поле vpn_key, переносим данные.
    # Если поле vpn_key отсутствует, этот шаг пропускается.
    user_columns = [col.name for col in db.get_columns('user')]
    if 'vpn_key' in user_columns:
        query = User.select().where(User.vpn_key.is_null(False))
        for user in query:
            try:
                # Если записи еще нет, создаем
                UserVPNKey.get(user=user, vpn_key=user.vpn_key)
            except peewee.DoesNotExist:
                UserVPNKey.create(user=user, vpn_key=user.vpn_key)
                app_logger.debug(f"Перенесён VPN ключ для пользователя {user.user_id}")
        # 3. Удаляем столбец vpn_key из таблицы User
        try:
            migrate(
                migrator.drop_column('user', 'vpn_key')
            )
            app_logger.debug("Столбец vpn_key удалён из таблицы User.")
        except Exception as e:
            app_logger.error(f"Ошибка при удалении столбца vpn_key: {e}")
    else:
        app_logger.debug("Столбец vpn_key уже отсутствует, пропускаем перенос данных.")
