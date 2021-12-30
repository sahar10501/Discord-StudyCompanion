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
from models import StudySession, Participant, History
from tortoise.contrib.quart import register_tortoise
import pytz
from datetime import datetime

datetime.utcnow().replace(tzinfo=pytz.utc)
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
        # Checks if the user is already a manager of a session or an active participant
        if not await StudySession.filter(manager=ses["USER_PAYLOAD"]["user_id"]).exists() \
                or not await Participant.filter(discord_id=ses["USER_PAYLOAD"]["user_id"], active=True).exists():
            if "stage_session" in request.headers["X-Custom-Header"]:
                payload = await request.get_json()
                users_id = payload["users_id"]
                if 1 <= len(users_id) <= 4:
                    channel_name = payload["topic"]
                    desc = payload["desc"]
                    guild_id = ses["USER_GUILD"][0]
                    user_info = ses["USER_PAYLOAD"]
                    user_info_username = user_info["username"]
                    user_info_id = user_info["user_id"]
                    dm_channels = await client.init_multiple_dm_channels(users_id)
                    dm_channel_id = [dm_channel["id"] for dm_channel in dm_channels]
                    # make it option for the user to select if he wishes to create a discord voice channel
                    voice_channel = await client.create_voice_channel(guild_id=guild_id, channel_name=channel_name,
                                                                      users_limit=len(users_id))
                    voice_channel_id = voice_channel["id"]
                    invite_msg = await client.create_invite(channel_id=voice_channel_id)
                    inv_msg_id = await client.inv_multiple_users(dm_channel_id, invite=invite_msg)

                    active_session_payload = dict(zip(users_id, list((zip(dm_channel_id, inv_msg_id)))))
                    ses["ACTIVE_SESSION_PAYLOAD"] = active_session_payload
                    # stores in db
                    study_session = await StudySession.create(name=channel_name if channel_name
                                                              else "No Topic Study Room",
                                                              manager=user_info_id,
                                                              guild=guild_id,
                                                              manager_username=user_info_username,
                                                              voice_channel_id=voice_channel_id,
                                                              desc=desc if len(desc) > 0 else "No Description")
                    for user_id in users_id:
                        await Participant.create(session_id=study_session.id, discord_id=user_id, active=False)
                    await Participant.create(session_id=study_session.id, discord_id=user_info_id, active=True,
                                             joined=datetime.now(pytz.utc))
                    # add an option for the session host to start his time count only when everyone joins
                else:
                    return "Wrong user number"

        if "stop_session" in request.headers["X-Custom-Header"]:
            if StudySession.filter(manager=ses["USER_PAYLOAD"]["user_id"]):
                query = await StudySession.filter(manager=ses["USER_PAYLOAD"]["user_id"]).first()
                participants = await Participant.filter(session=query.id, active=True).all()
                # delete all the inactive invited users!!
                current_time = datetime.now(pytz.utc)
                for participant in participants:
                    duration = current_time - participant.joined
                    # Change later to 300
                    if duration.total_seconds() >= 5:
                        await History.create(session_name=query.name, desc=query.desc, user_id=participant.discord_id,
                                             duration=duration)
                await History.create(session_name=query.name, desc=query.desc, user_id=query.manager,
                                     duration=current_time - query.start)
                await client.delete_channel(channel_id=query.voice_channel_id)
                await query.delete()
                ses["ACTIVE_SESSION_PAYLOAD"] = None
                # need to remove the invite link too and maybe the message aswell
                return redirect("/")

        if "leave_session" in request.headers["X-Custom-Header"]:
            user_session = await Participant.filter(discord_id=ses["USER_PAYLOAD"]["user_id"]).first()
            session_info = await StudySession.filter(id=user_session.session_id).first()
            current_time = datetime.now(pytz.utc)
            duration = current_time - user_session.joined
            await History.create(session_name=session_info.name,
                                 desc=session_info.desc if session_info.desc is not None else "No Description",
                                 user_id=user_session.discord_id,
                                 duration=duration)
            await user_session.delete()
            return redirect("/")

        if "check_user" in request.headers["X-Custom-Header"]:
            if StudySession.filter(manager=ses["USER_PAYLOAD"]["user_id"]).exists:
                query = await StudySession.filter(manager=ses["USER_PAYLOAD"]["user_id"]).first()
                check_user = await request.get_json()
                check_user_id = check_user["user_id"]
                if not await Participant.filter(discord_id=check_user_id, active=True).exists() \
                        and not await StudySession.filter(manager=check_user_id).exists():
                    active_sessions = ses["ACTIVE_SESSION_PAYLOAD"]
                    active_dm_session = active_sessions[check_user_id]
                    check_reaction = await client.check_reaction(active_dm_session)
                    active_user = list(user for user in check_reaction if user["id"] != '848992662250192916')
                    if active_user:
                        await Participant.filter(discord_id=check_user_id, session_id=query.id)\
                            .update(active=True, joined=datetime.now(pytz.utc))
                        return "Joined"
                    else:
                        return "Invited"
                else:
                    "User already in a session"
            else:
                "You are not a session manager"
        return "hello"

    else:
        user_guild_payload = ses["USER_GUILD"]
        user_payload = ses["USER_PAYLOAD"]
        if ses.get("GUILD_USERS") is None:
            # give the user an option to refresh his list of guild users
            response = await client.get_guild_members(user_guild_payload[0], ses["USER_PAYLOAD"]["user_id"])
            ses["GUILD_USERS"] = response

        # manager view
        if await StudySession.filter(manager=ses["USER_PAYLOAD"]["user_id"]).exists():
            user_payload = ses["USER_PAYLOAD"]
            guild_users = ses["GUILD_USERS"]
            # This is repeated and I need to turn this into a function
            session_info = await StudySession.filter(manager=ses["USER_PAYLOAD"]["user_id"]).first()
            active_session_users = await Participant.exclude(discord_id=ses["USER_PAYLOAD"]["user_id"])\
                .filter(session_id=session_info.id).all()
            invited_users_payload = {}
            for user in active_session_users:
                if str(user.discord_id) in guild_users:
                    invited_users_payload = {str(user.discord_id): guild_users[str(user.discord_id)]}
                    invited_users_payload[str(user.discord_id)]["active"] = user.active
            return await render_template("index.html", session_info=session_info,
                                         active_users_partic=invited_users_payload,
                                         duration=session_info.start,
                                         user_payload=user_payload,
                                         manager=True)

        # participant view
        elif await Participant.filter(discord_id=ses["USER_PAYLOAD"]["user_id"], active=True).exists() \
                and not await StudySession.filter(manager=ses["USER_PAYLOAD"]["user_id"]).exists():
            user_payload = ses["USER_PAYLOAD"]
            user_session = await Participant.filter(discord_id=ses["USER_PAYLOAD"]["user_id"], active=True).first()
            session_info = await StudySession.filter(id=user_session.session_id).first()
            active_session_users = await Participant.exclude(discord_id=ses["USER_PAYLOAD"]["user_id"])\
                .filter(session_id=user_session.session_id, active=True).all()
            if session_info.guild != ses["USER_GUILD"][0]:
                response = await client.get_guild_members(session_info.guild)
                ses["GUILD_USERS"] = response
            guild_users = ses["GUILD_USERS"]
            invited_users_payload = {}
            for user in active_session_users:
                if str(user.discord_id) in guild_users:
                    invited_users_payload = {str(user.discord_id): guild_users[str(user.discord_id)]}
                    invited_users_payload[str(user.discord_id)]["active"] = user.active
            return await render_template("index.html",
                                         session_info=session_info,
                                         active_users_partic=invited_users_payload,
                                         duration=user_session.joined.isoformat(),
                                         user_payload=user_payload,
                                         participant=True)

        return await render_template("index.html",
                                     guild_users=ses["GUILD_USERS"],
                                     user_payload=user_payload)


@QUART_APP.route("/login/")
async def login():
    discord.revoke()
    return await discord.create_session(scope=[
        "connections", "email", "identify", "guilds", "guilds.join",
        "gdm.join", "messages.read"
    ])


@QUART_APP.route("/history/")
async def history():
    query = await History.filter(user_id=ses["USER_PAYLOAD"]["user_id"]).all()
    user_history = {query.index(study_session): {"name": study_session.session_name,
                                                 "duration": str(study_session.duration).split(".")[0],
                                                 "desc": study_session.desc} for study_session in query}
    return await render_template("history.html", user_payload=ses["USER_PAYLOAD"], user_history=user_history)


@QUART_APP.route("/guild/", methods=["POST", "GET"])
async def guild():
    if request.method == "POST":
        if "guild_id" in await request.get_json(force=True):
            user_guild_id = await request.get_json(force=True)
            guild_payload = ses["GUILD_PAYLOAD"]
            if user_guild_id["guild_id"] in list(guild_payload["user"]):
                ses["USER_GUILD"] = [user_guild_id["guild_id"],
                                     guild_payload["user"][user_guild_id["guild_id"]]["name"],
                                     guild_payload["user"][user_guild_id["guild_id"]]["icon"]]
            ses["GUILD_USERS"] = None

        return redirect("/guild")
    else:
        if ses.get("GUILD_PAYLOAD") is None:
            # make an option for the client to refresh his guild list
            token = await discord.get_authorization_token()
            user = await client.get_user_info(token)
            user_guilds_response = await client.get_user_guilds(token)
            bot_guilds_response = await client.get_bot_guilds()
            ses["USER_PAYLOAD"] = {
                "user_id": user["id"],
                "avatar": user["avatar"],
                "username": user["username"]
            }
            ses["GUILD_PAYLOAD"] = {"user": {
                user_guild["id"]: {
                    "name": user_guild["name"],
                    "icon": user_guild["icon"]} for user_guild in user_guilds_response},
                "bot": {
                    bot_guild["id"]: {
                        "name": bot_guild["name"],
                        "icon": bot_guild["icon"]} for bot_guild in bot_guilds_response}}

        return await render_template("guild.html",
                                     bot_guilds=ses["GUILD_PAYLOAD"]["bot"],
                                     user_guilds=ses["GUILD_PAYLOAD"]["user"],
                                     user_payload=ses["USER_PAYLOAD"])


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
