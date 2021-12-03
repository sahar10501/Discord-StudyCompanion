from discord.ext import commands


class Example(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print('Bot is ready!.')

    @commands.command()
    async def change(self, ctx):
        await ctx.send('change')
        async for member in ctx.guild.fetch_members(limit=1000):
            print(member.name)

def setup(bot):
    bot.add_cog(Example(bot))
