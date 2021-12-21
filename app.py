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
        if not await StudySession.filter(manager=ses["user_id"]).exists() \
                or not await Participant.filter(discord_id=ses["user_id"]).exists():
            if "invite_list" in request.headers["X-Custom-Header"]:
                payload = await request.get_json()
                users_id = payload["users_id"]
                if 1 <= len(users_id) <= 3:
                    guild_id = ses["user_guild_id"]
                    user_id = ses["user_id"]
                    user_info = ses["user_payload"]
                    user_info_username = user_info["username"]
                    channel_name = payload["topic"]
                    desc = payload["desc"]

                    dm_channels = await client.init_multiple_dm_channels(users_id)
                    dm_channel_id = [dm_channel["id"] for dm_channel in dm_channels]
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
                    await Participant.create(session_id=study_session.id, discord_id=ses["user_id"])
                else:
                    return "Wrong user number"

        if "stop_session" in request.headers["X-Custom-Header"]:
            if StudySession.filter(manager=ses["user_id"]):
                query = await StudySession.filter(manager=ses["user_id"]).first()
                participants = await Participant.filter(session=query.id).all()
                current_time = datetime.now(pytz.utc)
                for participant in participants:
                    duration = current_time - participant.start
                    # Change later to 300
                    if duration.total_seconds() >= 5:
                        await History.create(session_name=query.name,
                                             desc=query.desc,
                                             user_id=participant.discord_id,
                                             duration=duration)
                        # user_time = timedelta(seconds=history.duration.total_seconds())

                await client.delete_channel(channel_id=query.voice_channel_id)
                await query.delete()
                ses["active_session_payload"] = None
                # need to remove the invite link too and maybe the message aswell
                return redirect("/")

        if "leave_session" in request.headers["X-Custom-Header"]:
            user_id = ses["user_id"]
            user_session = await Participant.filter(discord_id=user_id).first()
            session_info = await StudySession.filter(id=user_session.session_id).first()
            current_time = datetime.now(pytz.utc)
            duration = current_time - user_session.start
            await History.create(session_name=session_info.name,
                                 desc=session_info.desc if session_info.desc is not None else "No Description",
                                 user_id=user_session.discord_id,
                                 duration=duration)
            await user_session.delete()
            return redirect("/")

        if "check_user" in request.headers["X-Custom-Header"]:
            if StudySession.filter(manager=ses["user_id"]).exists:
                # later store the active session somewhere else, maybe a cookie
                query = await StudySession.filter(manager=ses["user_id"]).first()
                check_user = await request.get_json()
                check_user_id = check_user["user_id"]
                active_sessions = ses["active_session_payload"]
                active_dm_session = active_sessions[check_user_id]
                active_session_users = ses["active_session_users"]

                active_user = await client.check_reaction(active_dm_session)
                if active_user[0]["id"] in active_sessions not in active_session_users:
                    test = await Participant.create(session_id=query.id, discord_id=active_user[0]["id"])
                    active_session_users.append(active_user[0]["id"])
                    ses["active_session_users"] = active_session_users
                    return "Joined"
                else:
                    return "Invited"
            else:
                "You are not a session manager"
        return "hello"

    else:
        guild_id = ses["user_guild_id"]
        user_payload = ses["user_payload"]
        if ses.get("guild_users") is None:
            # saving all the users in the chosen guild
            response = await client.get_guild_members(guild_id)
            guild_users = {
                user["user"]["id"]: {
                    "username": user["user"]["username"],
                    "avatar": user["user"]["avatar"]}
                for user in response if user["user"]["id"] != str(ses["user_id"]) and "bot" not in user["user"]}
            ses["guild_users"] = guild_users

        # manager view: need to work on var naming for manager and participant
        if await StudySession.filter(manager=ses["user_id"]).exists():
            # need to reorder
            session_manager = True
            session_info = await StudySession.filter(manager=ses["user_id"]).first()
            user_session = await Participant.filter(discord_id=ses["user_id"]).first()
            guild_users = ses["guild_users"]
            active_session_users = await Participant.exclude(discord_id=ses["user_id"]).filter(session_id=user_session.session_id).all()
            # a list of the users id that are participating in the session without the user it self
            active_users_id = [str(active_user.discord_id) for active_user in active_session_users]
            active_users_payload = {user: guild_users[user] for user in active_users_id if user in guild_users}
            active_ses = ses["active_session_payload"]
            users_id = [active for active in active_ses]
            users_info = {user: guild_users[user] for user in users_id}
            user_payload = ses["user_payload"]
            duration = datetime.now(pytz.utc) - user_session.start
            duration = str(duration).split(".")[0]
            # check the vars again, and maybe better name them
            #print(f"this is session_partic {user_session}\n this is session_partic by name {users_info}\n"
                  #f" this is active_user partic {active_users_payload}")
            return await render_template("index.html", session_info=session_info,
                                         session_partic=user_session,
                                         session_partic_byname=users_info,
                                         active_users_partic=active_users_payload,
                                         session_manager=session_manager,
                                         duration=duration,
                                         manager=True,
                                         user_payload=user_payload)

        # participant view
        elif await Participant.filter(discord_id=ses["user_id"]).exists():
            user_session = await Participant.filter(discord_id=ses["user_id"]).first()
            session_info = await StudySession.filter(id=user_session.session_id).first()
            # make sure that the stored guild users in the cookie is matching to the guild in the ses
            # he's joining
            if session_info.guild != ses["user_guild_id"]:
                response = await client.get_guild_members(session_info.guild)
                # refactor into a function
                guild_users = {
                    user["user"]["id"]: {
                        "username": user["user"]["username"],
                        "avatar": user["user"]["avatar"]}
                    for user in response if user["user"]["id"] != str(ses["user_id"])
                                            and "bot" not in user["user"]}
                ses["guild_users"] = guild_users
            user_payload = ses["user_payload"]
            guild_users = ses["guild_users"]
            session_users = await Participant.exclude(discord_id=ses["user_id"]).filter(session_id=user_session.session_id).all()
            active_users_id = [str(active_user.discord_id) for active_user in session_users]
            active_users_payload = {user: guild_users[user] for user in active_users_id if user in guild_users}
            duration = datetime.now(pytz.utc) - user_session.start
            formatted_dur = str(duration).split(".")[0]
            return await render_template("index.html",
                                         session_partic=user_session,
                                         duration=formatted_dur,
                                         active_users_partic=active_users_payload,
                                         participant=True,
                                         user_payload=user_payload,
                                         session_info=session_info)
        return await render_template("index.html",
                                     guild_users=ses["guild_users"],
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
    query = await History.filter(user_id=ses["user_id"]).all()
    user_history = {query.index(study_session): {"name": study_session.session_name,
                                                 "duration": str(study_session.duration).split(".")[0],
                                                 "desc": study_session.desc} for study_session in query}
    return await render_template("history.html", user_payload=ses["user_payload"],
                                 user_history=user_history)


@QUART_APP.route("/guild/", methods=["POST", "GET"])
async def guild():
    if request.method == "POST":
        if "guild_name" in await request.get_json(force=True):
            guild_name = await request.get_json(force=True)
            # I already got a list of guilds and stores it in session, better to use it again.
            # I can get the id from list of dicts much eaiser than what I did here. # (check example down "test")
            bot_guilds = await discord.bot_request("/users/@me/guilds", method="GET")
            #print(bot_guilds)
            test = [item["id"] for item in bot_guilds if item["name"] == guild_name] # do this instead
            #print(test)
            bot_guilds_info = [{"guild_name": bot_guild["name"], "id": bot_guild["id"]} for bot_guild in bot_guilds]
            #print(bot_guilds_info)
            user_guild_id = next(item for item in bot_guilds_info if item["guild_name"] == guild_name["guild_name"])
            #print(user_guild_id)
            ses["user_guild_id"] = user_guild_id["id"]
            ses["guild_users"] = None

        return redirect("/")
    else:
        if ses.get("user_guilds_list") is None:
            user = await discord.fetch_user()
            ses["user_id"] = user.id
            ses["user_payload"] = {
                "user_id": user.id,
                "avatar": user.avatar_hash,
                "username": user.username
            }
            user_guilds = await discord.fetch_guilds()
            #print(user_guilds[0].id)
            user_guilds = [str(name) for name in user_guilds]
            bot_guilds = await discord.bot_request("/users/@me/guilds", method="GET")
            # change it, get rid of repeating var name..
            bot_guilds_name = [str(name["name"]) for name in bot_guilds]
            ses["user_guilds_list"], ses["bot_guilds_list"] = user_guilds, bot_guilds_name
            #print("------")
            #print(ses["user_guilds_list"], ses["bot_guilds_list"])
            #print("------")
            # change naming "common guilds" to supported guilds
            # move everything to a dict with two keys, "supported guilds" & user_guilds
            # values will be: dicts with keys of the guild id and their value will be, avatar and name
            # currently it compares by name to check which guilds are supported.. this is wrong
            # need to switch to my client to fetch this info
        return await render_template("guild.html",
                                     guilds=ses["user_guilds_list"],
                                     common_guilds=ses["bot_guilds_list"], user_payload=ses["user_payload"])


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
