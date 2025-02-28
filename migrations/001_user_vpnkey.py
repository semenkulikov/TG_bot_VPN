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

    # 2. Получаем список столбцов таблицы user с помощью db.get_columns
    user_columns = [col.name for col in db.get_columns('user')]
    if 'vpn_key_id' in user_columns:
        # Используем сырой SQL для получения значений столбца vpn_key_id
        cursor = db.execute_sql('SELECT id, vpn_key_id FROM "user" WHERE vpn_key_id IS NOT NULL')
        rows = cursor.fetchall()
        for row in rows:
            user_pk = row[0]
            vpn_key_id_val = row[1]
            try:
                user_obj = User.get_by_id(user_pk)
            except User.DoesNotExist:
                app_logger.error(f"Пользователь с id={user_pk} не найден.")
                continue
            try:
                # Если запись ещё не существует, создаём её
                UserVPNKey.get(user=user_obj, vpn_key=vpn_key_id_val)
            except peewee.DoesNotExist:
                UserVPNKey.create(user=user_obj, vpn_key=vpn_key_id_val)
                app_logger.debug(f"Перенесён VPN ключ для пользователя {user_obj.user_id}")
        # 3. Удаляем столбец vpn_key_id из таблицы user
        try:
            migrate(
                migrator.drop_column('user', 'vpn_key_id')
            )
            app_logger.debug("Столбец vpn_key_id удалён из таблицы user.")
        except Exception as e:
            app_logger.error(f"Ошибка при удалении столбца vpn_key_id: {e}")
    else:
        app_logger.debug("Столбец vpn_key_id отсутствует, перенос данных не требуется.")
