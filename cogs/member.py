import discord
from discord.ext import commands

class membercog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot


    #memberコマンド
    @commands.slash_command(
        name="member",
        description="現在チャットルームにいるメンバーを表示"
    )

    async def member(self, ctx):
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

        await ctx.respond(
            "**メンバー一覧**\n" + info_text + f"\n合計人数: {len(member)}", 
            ephemeral=True
            )

def setup(bot):
    bot.add_cog(membercog(bot))
