
import discord
from discord.ext import commands
from datetime import datetime, timezone

GUILD = discord.Object(id=int('1026051164782993478'))

#年度ごとのロール規則
role_rules = {
    "2022" : (datetime(2022, 4, 1, tzinfo=timezone.utc),
              datetime(2023, 3, 31, tzinfo=timezone.utc),
              "22"),

    "2023" : (datetime(2023, 4, 1, tzinfo=timezone.utc),
              datetime(2024, 3, 31, tzinfo=timezone.utc),
              "23"),

    "2024" : (datetime(2024, 4, 1, tzinfo=timezone.utc),
              datetime(2025, 3, 31, tzinfo=timezone.utc),
              "24"),

    "2025" : (datetime(2025, 4, 1, tzinfo=timezone.utc),
              datetime(2026, 3, 31, tzinfo=timezone.utc),
              "25")
    }

class rolecog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(
        name="role",
        description="入会年度でロールを付与"
    )
    async def role(
            self,
            ctx: discord.Interaction,
            action: str,
            year: str
    ):
        if action != "add":
            await ctx.response.send_message("現在はaddのみ対応", ephemeral=True)
            return

        if year not in role_rules:
            await ctx.response.send_message("指定した年度は追加されていません", ephemeral=True)
            return

        start_date, end_date, role_name = role_rules[year]
        guild = ctx.guild
        role = discord.utils.get(guild.roles, name=role_name)

        if role is None:
            await ctx.response.send_message(f"{role_name} が見つかりません", ephemeral=True)
            return

        #仮メッセージ
        msg =  await ctx.send(f"{year}年度のロール付与を受け付けました", ephemeral=True)

        count = 0
        for member in guild.members:
            if member.bot:
                continue

            if member.joined_at and start_date <= member.joined_at <= end_date:
                if role not in member.roles:
                    await member.add_roles(role)
                count += 1

        await msg.edit(
            content = f"{year}年度の条件に合うメンバー{count}人に{role_name}を付与しました。"
        )

async def setup(bot):
    await bot.add_cog(rolecog(bot))



