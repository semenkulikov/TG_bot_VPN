import peewee

db = peewee.SqliteDatabase("database/database.db")


class BaseModel(peewee.Model):
    """ Базовая модель """
    class Meta:
        database = db


class User(BaseModel):
    """ Модель пользователя """
    user_id = peewee.CharField(unique=True)
    full_name = peewee.CharField()
    username = peewee.CharField()
    is_premium = peewee.BooleanField(null=True)


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
