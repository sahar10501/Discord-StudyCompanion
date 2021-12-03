from quart import Quart, redirect, render_template, request, url_for, jsonify
from quart import session as ses
from discord_client import DiscordClient
from hypercorn.asyncio import serve
from hypercorn.config import Config
from quart_discord import DiscordOAuth2Session, requires_authorization, Unauthorized
from helpers import login_required
import os
import asyncio
from http_client import AsyncHttpRequest
from dotenv import load_dotenv
import models
from quart import Quart, jsonify

from tortoise.contrib.quart import register_tortoise




QUART_APP = Quart(__name__)
config = Config()
load_dotenv()
config.bind = ["localhost:8080"]
QUART_APP.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
QUART_APP.config["TEMPLATES_AUTO_RELOAD"] = True
QUART_APP.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
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
        if 'invite_list' in request.headers['X-Custom-Header']:
            guild_id = ses["user_guild_id"]
            users = await request.get_json()
            users_id = users['users_id']
            users_amount = len(users_id)
            channel_name = users['topic']
            dm_channels = await client.init_dm_channels(users_id)
            dm_channel_id = [dm_channel["id"] for dm_channel in dm_channels]
            voice_channel = await client.create_channel(guild_id=guild_id, channel_name=channel_name,
                                                        users_limit=users_amount)
            voice_channel_id = voice_channel["id"]
            invite_msg = await client.create_invite(channel_id=voice_channel_id)
            await client.inv_multiple_users(dm_channel_id, invite=invite_msg)
        return 'hello'

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
            
        return await render_template("index.html", guild_users=ses['guild_users'])


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
            # Remember the guild - need to know the ID
            bot_guilds = await discord.bot_request("/users/@me/guilds", method="GET")
            bot_guilds_info = [{"guild_name": guild["name"], "id": guild["id"]} for guild in bot_guilds]
            user_guild_id = next(item for item in bot_guilds_info if item["guild_name"] == guid_name["guild_name"])
            ses["user_guild_id"] = user_guild_id["id"]
            ses["guild_users"] = None

        return redirect("/")
    else:
        if ses.get("user_guilds_list") is None:
            user_guilds = await discord.fetch_guilds()
            user_guilds = [str(name) for name in user_guilds]
            bot_guilds = await discord.bot_request("/users/@me/guilds", method="GET")
            bot_guilds_name = [str(name['name']) for name in bot_guilds]
            ses['user_guilds_list'], ses['bot_guilds_list'] = user_guilds, bot_guilds_name

        return await render_template("guild.html",
                                     guilds=ses['user_guilds_list'],
                                     common_guilds=ses['bot_guilds_list'])


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


@QUART_APP.route("/me/")
@requires_authorization
async def me():
    user = await discord.fetch_user()
    return await render_template("index.html")


asyncio.run(serve(QUART_APP, config))
