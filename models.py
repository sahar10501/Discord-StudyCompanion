from tortoise.models import Model
from tortoise import fields
from tortoise.validators import CommaSeparatedIntegerListValidator


class Session(Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(25)
    manager = fields.BigIntField()
    participants = fields.CharField(validators=[CommaSeparatedIntegerListValidator], max_length=150)
    guild = fields.BigIntField()
    start = fields.DatetimeField(auto_now_add=True)
    end = fields.DatetimeField(auto_now=True)
    #duration = fields.TimeDeltaField()
