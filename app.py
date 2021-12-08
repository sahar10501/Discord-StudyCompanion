from quart import Quart, redirect, render_template, request, url_for
from quart import session as ses
from hypercorn.asyncio import serve
from hypercorn.config import Config
from quart_discord import DiscordOAuth2Session, requires_authorization, Unauthorized
from helpers import login_required
import os
import asyncio
from clients import AsyncHttpRequest
from clients import DiscordClient
from dotenv import load_dotenv
from models import StudySession, Participant
from tortoise.contrib.quart import register_tortoise

QUART_APP = Quart(__name__)
config = Config()
load_dotenv()
config.bind = ["localhost:8080"]
QUART_APP.config["TEMPLATES_AUTO_RELOAD"] = True
QUART_APP.config["DISCORD_CLIENT_ID"] = os.getenv("DISCORD_CLIENT_ID")
QUART_APP.config["DISCORD_CLIENT_SECRET"] = os.getenv("DISCORD_CLIENT_SECRET")
QUART_APP.config["DISCORD_REDIRECT_URI"] = os.getenv("DISCORD_REDIRECT_URI")
QUART_APP.config["DISCORD_BOT_TOKEN"] = os.getenv("TOKEN")
QUART_APP.secret_key = b"61fca8b8c60e022044c2d67a4afb0c4f180f3b28c27785c8e32bc1c3f41c7d75"
discord = DiscordOAuth2Session(QUART_APP)
client = AsyncHttpRequest()
# init the database
register_tortoise(
    QUART_APP,
    db_url="sqlite://database.db",
    modules={"models": ["models"]},
    # ONLY FOR SQLITE
    generate_schemas=True,
)


@QUART_APP.before_serving
async def before_serving():
    loop = asyncio.get_event_loop()
    QUART_APP.discord_client = DiscordClient()
    await QUART_APP.discord_client.bot.login(os.getenv("TOKEN"))
    loop.create_task(QUART_APP.discord_client.bot.connect())


@QUART_APP.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@QUART_APP.route("/", methods=["POST", "GET"])
@requires_authorization
@login_required
async def homepage():
    if request.method == "POST":
        # Checks if the user is already a manager of a session
        if not await StudySession.filter(manager=ses["user_id"]):
            if "invite_list" in request.headers["X-Custom-Header"]:
                payload = await request.get_json()
                users_id = payload["users_id"]
                if 1 <= len(users_id) <= 3:
                    guild_id = ses["user_guild_id"]
                    user_id = ses["user_id"]
                    users_amount = len(users_id)
                    channel_name = payload["topic"]

                    dm_channels = await client.init_multiple_dm_channels(users_id)
                    dm_channel_id = [dm_channel["id"] for dm_channel in dm_channels]
                    voice_channel = await client.create_voice_channel(guild_id=guild_id, channel_name=channel_name,
                                                                      users_limit=users_amount)
                    voice_channel_id = voice_channel["id"]
                    invite_msg = await client.create_invite(channel_id=voice_channel_id)
                    inv_msg_id = await client.inv_multiple_users(dm_channel_id, invite=invite_msg)
                    # wrapping the session by a user id and his two values, msg_id and channel id
                    active_session_payload = dict(zip(users_id, list((zip(dm_channel_id, inv_msg_id)))))
                    ses["active_session_payload"] = active_session_payload

                    # stores in db
                    await StudySession.create(name=channel_name if channel_name else "No Topic Study Room",
                                              manager=user_id, guild=guild_id,
                                              voice_channel_id=voice_channel_id)
                else:
                    return "Wrong user number"
        if "start_session" in request.headers["X-Custom-Header"]:
            query = await StudySession.filter(manager=ses["user_id"]).first()
            await Participant.create(session_id=query.id, discord_id=336967207172964362)
        if "stop_session" in request.headers["X-Custom-Header"]:
            query = await StudySession.filter(manager=ses["user_id"]).first()
            await client.delete_channel(channel_id=query.voice_channel_id)
            # Delete the session
            await query.delete()
            ses["active_session_payload"] = None
            # need to remove the invite link too
            return await render_template("index.html", guild_users=ses["guild_users"])
        if "check_user" in request.headers["X-Custom-Header"]:
            check_user_id = await request.get_json()
            check_user_id = check_user_id["user_id"]
            active_sessions = ses["active_session_payload"]
            active_dm_session = active_sessions[check_user_id]
            user_reaction = await client.check_reaction(active_dm_session)
            if user_reaction[0]["id"] == check_user_id:
                
                return "Joined"
            else:
                return "Invited"

        return "hello"


    else:
        guild_id = ses["user_guild_id"]
        if ses.get("guild_users") is None:
            response = await client.get_guild_members(guild_id)
            # move to http_client
            guild_users = [{
                "user_id": user["user"]["id"],
                "username": user["user"]["username"],
                "avatar": user["user"]["avatar"]
            } for user in response]
            ses["guild_users"] = guild_users
        if await StudySession.filter(manager=ses["user_id"]).all():
            study_session = await StudySession.filter(manager=ses["user_id"]).first()
            user_info = await Participant.filter(discord_id=ses["user_id"]).first()
            # View the page as a ses manager
            return await render_template("index.html", session_manager=study_session, user_info=user_info)
        return await render_template("index.html", guild_users=ses["guild_users"])


@QUART_APP.route("/login/")
async def login():
    discord.revoke()
    return await discord.create_session(scope=[
        "connections", "email", "identify", "guilds", "guilds.join",
        "gdm.join", "messages.read"])


@QUART_APP.route("/guild/", methods=["POST", "GET"])
async def guild():
    if request.method == "POST":
        if "guild_name" in await request.get_json(force=True):
            guid_name = await request.get_json(force=True)
            # need to switch to my client
            bot_guilds = await discord.bot_request("/users/@me/guilds", method="GET")
            bot_guilds_info = [{"guild_name": bot_guild["name"], "id": bot_guild["id"]} for bot_guild in bot_guilds]
            user_guild_id = next(item for item in bot_guilds_info if item["guild_name"] == guid_name["guild_name"])
            ses["user_guild_id"] = user_guild_id["id"]
            ses["guild_users"] = None
            user_id = await discord.fetch_user()
            ses["user_id"] = user_id.id
        return redirect("/")
    else:
        if ses.get("user_guilds_list") is None:
            # need to switch to my client
            user_guilds = await discord.fetch_guilds()
            user_guilds = [str(name) for name in user_guilds]
            # need to switch to my client
            bot_guilds = await discord.bot_request("/users/@me/guilds", method="GET")
            bot_guilds_name = [str(name["name"]) for name in bot_guilds]
            ses["user_guilds_list"], ses["bot_guilds_list"] = user_guilds, bot_guilds_name
        return await render_template("guild.html",
                                     guilds=ses["user_guilds_list"],
                                     common_guilds=ses["bot_guilds_list"])


@QUART_APP.route("/callback/")
async def callback():
    await discord.callback()
    return redirect(url_for("guild"))


@QUART_APP.route("/logout")
async def logout():
    discord.revoke()
    ses.clear()
    return redirect("/")


@QUART_APP.errorhandler(Unauthorized)
async def redirect_unauthorized(e):
    return redirect(url_for("login"))


asyncio.run(serve(QUART_APP, config))
