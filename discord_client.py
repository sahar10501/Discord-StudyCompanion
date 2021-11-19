from discord.ext import commands
import discord
import os


class DiscordClient(commands.Cog):

    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        self.bot = commands.Bot(command_prefix="!", intents=intents)
        for filename in os.listdir("./cogs"):
            if filename.endswith(".py") and filename != "__init__.py":
                self.bot.load_extension(f'cogs.{filename[:-3]}')
