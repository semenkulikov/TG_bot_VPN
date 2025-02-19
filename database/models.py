import datetime
import os.path
import re

from config_data.config import BASE_DIR
import peewee

db = peewee.SqliteDatabase(os.path.join(BASE_DIR, "database/database.db"))


class BaseModel(peewee.Model):
    """ Базовая модель """
    class Meta:
        database = db


class Server(BaseModel):
    """ Модель сервера для подключения VPN """
    username = peewee.CharField()
    password = peewee.CharField()
    location = peewee.CharField()
    ip_address = peewee.CharField(unique=True)
    public_key = peewee.CharField(null=True, unique=True)


class VPNKey(BaseModel):
    """ Модель для VPN ключа. Привязан к серверу. Имеет qr код (картинка) для подключения """
    server = peewee.ForeignKeyField(Server, related_name="keys",
                                     on_delete="cascade",
                                     on_update="cascade")
    name = peewee.CharField()
    key = peewee.CharField(unique=True)
    qr_code = peewee.CharField()
    is_valid = peewee.BooleanField(default=True)
    created_at = peewee.DateTimeField(default=datetime.datetime.now())
    updated_at = peewee.DateTimeField(default=datetime.datetime.now())

    def extract_uuid(self) -> str | None:
        """
        Извлекает UUID из VLESS-ссылки ключа.
        """
        match = re.match(r'vless://([a-fA-F0-9-]{36})@', self.key)
        return match.group(1) if match else None


class User(BaseModel):
    """ Модель пользователя """
    user_id = peewee.CharField(unique=True)
    full_name = peewee.CharField()
    username = peewee.CharField()
    is_premium = peewee.BooleanField(null=True)
    is_subscribed = peewee.BooleanField(default=False)
    vpn_key = peewee.ForeignKeyField(VPNKey, related_name="users", null=True, on_update="set null",
                                     on_delete="set null")


class Group(BaseModel):
    """ Класс группы """
    group_id = peewee.CharField(unique=True)
    title = peewee.CharField()
    description = peewee.TextField(null=True)
    bio = peewee.TextField(null=True)
    invite_link = peewee.CharField(null=True)
    location = peewee.CharField(null=True)
    username = peewee.CharField(null=True)


def create_models():
    db.create_tables(BaseModel.__subclasses__())
