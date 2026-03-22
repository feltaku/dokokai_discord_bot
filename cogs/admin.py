
import discord
from discord.ext import commands

class admincog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.slash_command(name="logoff", description="botを終了する")
    async def logoff(self, ctx):
        await ctx.respond("botを停止します", ephemeral=True)
        await self.bot.close()

def setup(bot):
    bot.add_cog(admincog(bot))
