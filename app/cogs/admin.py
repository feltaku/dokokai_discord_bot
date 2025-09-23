
import discord
from discord import app_commands
from discord.ext import commands

class admincog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="logoff", description="botを終了する")
    async def logoff(self, interaction: discord.Interaction):
        await interaction.response.send_message("botを停止します", ephemeral=True)
        await self.bot.close()

async def setup(bot):
    await bot.add_cog(admincog(bot))