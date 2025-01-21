import datetime
import os.path

from config_data.config import BASE_DIR
import peewee

db = peewee.SqliteDatabase(os.path.join(BASE_DIR, "database/database.db"))


class BaseModel(peewee.Model):
    """ Базовая модель """
    class Meta:
        database = db


class Server(BaseModel):
    """ Модель сервера для подключения VPN """
    server_id = peewee.CharField(unique=True)
    username = peewee.CharField()
    password = peewee.CharField()
    location = peewee.CharField()
    port = peewee.IntegerField()
    ip_address = peewee.CharField(unique=True)


class VPNKey(BaseModel):
    """ Модель для VPN ключа. Привязан к серверу. Имеет qr код (картинка) для подключения """
    key_id = peewee.CharField(unique=True)
    server = peewee.ForeignKeyField(Server, related_name="keys")
    name = peewee.CharField()
    key = peewee.CharField(unique=True)
    qr_code = peewee.CharField(unique=True)
    is_valid = peewee.BooleanField(default=True)
    created_at = peewee.DateTimeField(default=datetime.datetime.now())
    updated_at = peewee.DateTimeField(default=datetime.datetime.now())


class User(BaseModel):
    """ Модель пользователя """
    user_id = peewee.CharField(unique=True)
    full_name = peewee.CharField()
    username = peewee.CharField()
    is_premium = peewee.BooleanField(null=True)
    is_subscribed = peewee.BooleanField(default=False)
    vpn_key = peewee.ForeignKeyField(VPNKey, related_name="users", null=True)


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
