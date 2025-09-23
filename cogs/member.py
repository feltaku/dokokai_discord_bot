import discord
from discord.ext import commands

class membercog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot


    #memberコマンド
    @commands.hybrid_command(
        name="member",
        description="現在チャットルームにいるメンバーを表示"
    )

    async def member(self, ctx: commands.Context):
        channel = ctx.channel

        if isinstance(channel, discord.TextChannel):
            member = [m for m in channel.members if not m.bot]

        elif isinstance(channel, discord.VoiceChannel):
            await ctx.send("なんでボイチャでやるのさ")
            return

        else:
            await ctx.send("このチャンネルではメンバーを取得できません")
            return

        if not member:
            await ctx.send("メンバーが存在しません")
            return

        info_lines = [f"{member.display_name} ({str(member)})" for member in member]
        info_text = "\n".join(info_lines)

        await ctx.send("**メンバー一覧**", ephemeral=True)
        await ctx.send(info_text, ephemeral=True)
        await ctx.send(f"合計人数: {len(member)}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(membercog(bot))