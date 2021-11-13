import asyncio
from quart import Quart, redirect, url_for, render_template
from discord_client import DiscordClient
from hypercorn.asyncio import serve
from hypercorn.config import Config
from dotenv import load_dotenv
import os
from quart_discord import DiscordOAuth2Session, requires_authorization, Unauthorized

QUART_APP = Quart(__name__)
load_dotenv()
config = Config()
config.bind = ["localhost:8080"]
QUART_APP.secret_key = b"random bytes representing quart secret key"
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

@QUART_APP.route("/")
async def homepage():
    return await render_template("index.html")

@QUART_APP.route("/login/")
async def login():
    return await discord.create_session()


@QUART_APP.route("/callback/")
async def callback():
    await discord.callback()
    return redirect(url_for(".me"))


@QUART_APP.errorhandler(Unauthorized)
async def redirect_unauthorized(e):
    return redirect(url_for("login"))


@QUART_APP.route("/me/")
@requires_authorization
async def me():
    user = await discord.fetch_user()

    return await render_template("index.html")


asyncio.run(serve(QUART_APP, config))
