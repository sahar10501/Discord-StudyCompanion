from quart import Quart, redirect, render_template, request, url_for, session
from discord_client import DiscordClient
from hypercorn.asyncio import serve
from hypercorn.config import Config
from quart_discord import DiscordOAuth2Session, requires_authorization, Unauthorized
from helpers import login_required
from dotenv import load_dotenv
import os
import asyncio

QUART_APP = Quart(__name__)
load_dotenv()
config = Config()
config.bind = ["localhost:8080"]
QUART_APP.secret_key = b"random bytes representing quart secret key"
QUART_APP.config["TEMPLATES_AUTO_RELOAD"] = True
QUART_APP.config["DISCORD_CLIENT_ID"] = os.getenv("DISCORD_CLIENT_ID")
QUART_APP.config["DISCORD_CLIENT_SECRET"] = os.getenv("DISCORD_CLIENT_SECRET")
QUART_APP.config["DISCORD_REDIRECT_URI"] = os.getenv("DISCORD_REDIRECT_URI")
QUART_APP.config["DISCORD_BOT_TOKEN"] = os.getenv("TOKEN")
discord = DiscordOAuth2Session(QUART_APP)


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


@QUART_APP.route("/")
@requires_authorization
@login_required
async def homepage():
    return await render_template("index.html")


@QUART_APP.route("/login/")
async def login():
    discord.revoke()
    return await discord.create_session(scope=["guilds"])


@QUART_APP.route("/guild/", methods=["POST", "GET"])
async def guild():
    """ Here the user chooses the guild which he wishes to interact with
        - Checking the guild the bot and user is in and storing in session the guild
          the user chose
    """
    if request.method == "POST":
        if "guild_name" in await request.get_json(force=True):
            guid_name = await request.get_json(force=True)
            bot_guilds = await discord.bot_request("/users/@me/guilds", method="GET")
            bot_guilds_info = [{"guild_name": guild['name'], "id": guild['id']} for guild in bot_guilds]
            user_guild_id = next(item for item in bot_guilds_info if item["guild_name"] == guid_name['guild_name'])
            # clears session and stores the guild the user chose
            session.clear()
            session["user_guild_id"] = user_guild_id['id']

            #bot_guilds_info_1 = bot_guilds_info[0]
            #user_guild_input_id = {k: bot_guilds_info_1[k] for k in bot_guilds_info_1 if k in guid_name and bot_guilds_info_1[k] == guid_name[k]}
            #print(user_guild_input_id)
            #x = dict(a=1, b=2)
            #y = dict(a=2, b=2)
            #shared_items = {k: x[k] for k in x if k in y and x[k] == y[k]}
            #print(shared_items)

        return redirect("/")

    else:
        user_guilds = await discord.fetch_guilds()
        user_guilds = [str(name) for name in user_guilds]
        bot_guilds = await discord.bot_request("/users/@me/guilds", method="GET")
        bot_guilds_name = [str(name['name']) for name in bot_guilds]

        return await render_template("guild.html", guilds=user_guilds, common_guilds=bot_guilds_name)


@QUART_APP.route("/callback/")
async def callback():
    await discord.callback()
    return redirect(url_for("guild"))


@QUART_APP.route("/logout")
async def logout():
    discord.revoke()
    session.clear()
    return redirect("/")


@QUART_APP.errorhandler(Unauthorized)
async def redirect_unauthorized(e):
    return redirect(url_for("login"))


asyncio.run(serve(QUART_APP, config))
