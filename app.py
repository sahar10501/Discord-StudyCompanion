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
        # Checks if the user is already a manager of a session
        if not await StudySession.filter(manager=ses["USER_PAYLOAD"]["user_id"]).exists() \
                or not await Participant.filter(discord_id=ses["USER_PAYLOAD"]["user_id"], active=True).exists():
            if "invite_list" in request.headers["X-Custom-Header"]:
                payload = await request.get_json()
                users_id = payload["users_id"]
                if 1 <= len(users_id) <= 4:
                    guild_id = ses["user_guild_id"]
                    user_id = ses["USER_PAYLOAD"]["user_id"]
                    user_info = ses["USER_PAYLOAD"]
                    user_info_username = user_info["username"]
                    channel_name = payload["topic"]
                    desc = payload["desc"]
                    dm_channels = await client.init_multiple_dm_channels(users_id)
                    dm_channel_id = [dm_channel["id"] for dm_channel in dm_channels]
                    # make it option for the user to select if he wishes to create a discord voice channel
                    # when creating the study session, maybe make an option to create a text channel and then
                    # log the channel
                    voice_channel = await client.create_voice_channel(guild_id=guild_id,
                                                                      channel_name=channel_name,
                                                                      users_limit=len(users_id))
                    voice_channel_id = voice_channel["id"]
                    invite_msg = await client.create_invite(channel_id=voice_channel_id)
                    inv_msg_id = await client.inv_multiple_users(dm_channel_id, invite=invite_msg)

                    # wrapping the session by a user id and his two values, msg_id and channel id
                    active_session_payload = dict(zip(users_id, list((zip(dm_channel_id, inv_msg_id)))))
                    ses["active_session_payload"] = active_session_payload
                    ses["active_session_users"] = []
                    # stores in db
                    study_session = await StudySession.create(name=channel_name if channel_name
                                                              else "No Topic Study Room",
                                                              manager=user_id,
                                                              guild=guild_id,
                                                              manager_username=user_info_username,
                                                              voice_channel_id=voice_channel_id,
                                                              desc=desc if len(desc) > 0 else "No Description")
                    for user_id in users_id:
                        await Participant.create(session_id=study_session.id, discord_id=user_id, active=False)
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
                        await History.create(session_name=query.name,
                                             desc=query.desc,
                                             user_id=participant.discord_id,
                                             duration=duration)
                await History.create(session_name=query.name,
                                     desc=query.desc,
                                     user_id=query.manager,
                                     duration=current_time - query.start)
                # user_time = timedelta(seconds=history.duration.total_seconds())

                await client.delete_channel(channel_id=query.voice_channel_id)
                await query.delete()
                ses["active_session_payload"] = None
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
                # later store the active session somewhere else, maybe a cookie
                query = await StudySession.filter(manager=ses["USER_PAYLOAD"]["user_id"]).first()
                check_user = await request.get_json()
                check_user_id = check_user["user_id"]
                if not await Participant.filter(discord_id=check_user_id, active=True).exists() \
                        and not await StudySession.filter(manager=check_user_id).exists():
                    active_sessions = ses["active_session_payload"]
                    active_dm_session = active_sessions[check_user_id]
                    active_session_users = ses["active_session_users"]
                    active_user = await client.check_reaction(active_dm_session)
                    if active_user[0]["id"] in active_sessions not in active_session_users:
                        await Participant.filter(discord_id=active_user[0]["id"], session_id=query.id).update(
                            active=True, joined=datetime.now(pytz.utc))
                        active_session_users.append(active_user[0]["id"])
                        ses["active_session_users"] = active_session_users
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
        if ses.get("guild_users") is None:
            # saving all the users in the chosen guild, give the user an option to refresh his list
            response = await client.get_guild_members(user_guild_payload[0])
            guild_users = {
                user["user"]["id"]: {
                    "username": user["user"]["username"],
                    "avatar": user["user"]["avatar"]}
                for user in response if
                user["user"]["id"] != str(ses["USER_PAYLOAD"]["user_id"]) and "bot" not in user["user"]}
            ses["GUILD_USERS"] = guild_users

        # manager view
        if await StudySession.filter(manager=ses["USER_PAYLOAD"]["user_id"]).exists():
            # need to reorder
            session_manager = True
            session_info = await StudySession.filter(manager=ses["USER_PAYLOAD"]["user_id"]).first()
            guild_users = ses["GUILD_USERS"]
            active_session_users = await Participant. \
                exclude(discord_id=ses["USER_PAYLOAD"]["user_id"]). \
                filter(session_id=session_info.id).all()
            active_users_id = [str(active_user.discord_id) for active_user in active_session_users]
            active_users_payload = {user: guild_users[user] for user in active_users_id if user in guild_users}
            for user in active_session_users:
                if str(user.discord_id) in active_users_payload:
                    active_users_payload[str(user.discord_id)]["active"] = user.active
            # a list of the users id that are participating in the session
            # for user in actives_payload
            user_payload = ses["USER_PAYLOAD"]
            # check the vars again, and maybe better name them
            # print(f"this is session_partic {user_session}\n this is session_partic by name {users_info}\n"
            # f" this is active_user partic {active_users_payload}")
            return await render_template("index.html", session_info=session_info,
                                         session_participants=active_session_users,
                                         active_users_partic=active_users_payload,
                                         session_manager=session_manager,
                                         duration=session_info.start,
                                         manager=True,
                                         user_payload=user_payload)

        # participant view
        elif await Participant.filter(discord_id=ses["USER_PAYLOAD"]["user_id"], active=True).exists():
            user_session = await Participant.filter(discord_id=ses["USER_PAYLOAD"]["user_id"], active=True).first()
            session_info = await StudySession.filter(id=user_session.session_id).first()
            # comparing the key[user_guild_id] of the stored users dict to the current active session
            # in order to refresh the list of users stored in browser
            if session_info.guild != ses["user_guild_id"]:
                response = await client.get_guild_members(session_info.guild)
                # refactor into a function (repeating twice)
                guild_users = {
                    user["user"]["id"]: {
                        "username": user["user"]["username"],
                        "avatar": user["user"]["avatar"]}
                    for user in response if user["user"]["id"] != str(ses["USER_PAYLOAD"]["user_id"])
                                            and "bot" not in user["user"]}
                ses["GUILD_USERS"] = guild_users
            user_payload = ses["USER_PAYLOAD"]
            guild_users = ses["GUILD_USERS"]
            session_users = await Participant.exclude(discord_id=ses["USER_PAYLOAD"]["user_id"]).filter(
                session_id=user_session.session_id).all()
            active_users_id = [str(active_user.discord_id) for active_user in session_users]
            active_users_payload = {user: guild_users[user] for user in active_users_id if user in guild_users}
            return await render_template("index.html",
                                         session_partic=user_session,
                                         duration=user_session.joined.isoformat(),
                                         active_users_partic=active_users_payload,
                                         participant=True,
                                         user_payload=user_payload,
                                         session_info=session_info)

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
    return await render_template("history.html", user_payload=ses["USER_PAYLOAD"],
                                 user_history=user_history)


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
