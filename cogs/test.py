import discord
from discord.ext import commands
import asyncio

GUILD = discord.Object(id=int('1026051164782993478'))

class testcog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.slash_command(
        name="test",
        description="test command"
    )

    async def test(self, ctx):
            msg = await ctx.respond("テキスト", ephemeral=True)

            await asyncio.sleep(3)

            await msg.edit(content="編集済み")

def setup(bot):
    bot.add_cog(testcog(bot))
