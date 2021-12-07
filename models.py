from tortoise.models import Model
from tortoise import fields


class StudySession(Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(25)
    manager = fields.BigIntField()
    guild = fields.BigIntField()
    voice_channel_id = fields.BigIntField()
    # duration = fields.TimeDeltaField()


class Participant(Model):
    id = fields.IntField(pk=True)
    session: fields.ForeignKeyRelation[StudySession] = fields.ForeignKeyField("models.StudySession",
                                                                              related_name="session_id",
                                                                              to_field="id")
    discord_id = fields.BigIntField(unique=True)
    start = fields.DatetimeField(auto_now_add=True)
    end = fields.DatetimeField(auto_now=True)
