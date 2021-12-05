from quart import session, redirect
from functools import wraps
from models import Session


def login_required(f):
    """
    Verify that the user chose a guild
    """
    @wraps(f)
    async def decorated_function(*args, **kwargs):
        if session.get("user_guild_id") is None:
            return redirect("/guild")
        return await f(*args, **kwargs)
    return decorated_function


async def active_session(session):
    print('test')
    if await Session.filter(participants=session).all():
        test = await Session.filter(participants=session).all()
        print(test)
        return True
    else:
        print('test')
        return False
