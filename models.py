from tortoise.models import Model
from tortoise import fields
from tortoise.validators import CommaSeparatedIntegerListValidator


class Users(Model):
    id = fields.IntField(pk=True)
    session_name = fields.CharField(25)
    session_manager = fields.BigIntField()
    participants = fields.CharField(validators=[CommaSeparatedIntegerListValidator], max_length=150)
    start_time = fields.DatetimeField(auto_now_add=True)
    end_time = fields.DatetimeField(auto_now=True)
    duration = fields.TimeDeltaField()
