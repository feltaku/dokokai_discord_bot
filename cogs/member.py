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

        header = "**メンバー一覧**\n"
        footer = f"\n合計人数: {len(member)}"

        messages = []
        current = header

        for line in info_lines:
            add_line = line + "\n"
            if len(current) + len(add_line) + len(footer) > 2000:
                messages.append(current.rstrip())
                current = add_line
            else:
                current += add_line

        current += footer
        messages.append(current.rstrip())

        await ctx.respond(messages[0], ephemeral=True)

        for msg in messages[1:]:
            await ctx.send_followup(msg, ephemeral=True)

def setup(bot):
    bot.add_cog(membercog(bot))
