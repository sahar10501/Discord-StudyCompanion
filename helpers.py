from quart import session, redirect
from functools import wraps


def login_required(f):
    """
    Verify that the user chose a guild
    """
    @wraps(f)
    async def decorated_function(*args, **kwargs):
        if session.get("USER_GUILD") is None:
            return redirect("/guild")
        return await f(*args, **kwargs)
    return decorated_function
