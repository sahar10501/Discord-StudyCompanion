from quart import session, redirect
from functools import wraps


def login_required(f):
    """
    Decorate routes to require login.
    https://flask.palletsprojects.com/en/1.1.x/patterns/viewdecorators/
    """
    @wraps(f)
    async def decorated_function(*args, **kwargs):
        if session.get("user_guild_id") is None:
            return redirect("/guild")
        return await f(*args, **kwargs)
    return decorated_function
