import discord
from discord.ext import commands
from discord.commands import slash_command
from datetime import datetime, timezone


class rolecog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def make_year_range(self, year_str: str):
        try:
            year_int = int(year_str)
        except ValueError:
            return None

        return (
            datetime(year_int, 4, 1, tzinfo=timezone.utc),
            datetime(year_int + 1, 4, 1, tzinfo=timezone.utc),
            year_str[-2:]
        )

    @slash_command(name="role", description="年度ごとにロールを付与します")
    async def role(
        self,
        ctx,
        action: str,
        year: str,
        role_name: str
    ):
        if action != "add":
            await ctx.respond("action には add を指定してください", ephemeral=True)
            return

        guild = ctx.guild
        role = discord.utils.get(guild.roles, name=role_name)

        if role is None:
            await ctx.respond(f"ロール {role_name} が見つかりません", ephemeral=True)
            return

        year_range = self.make_year_range(year)
        if year_range is None:
            await ctx.respond("年度は 2026 のように4桁の数字で入力してください", ephemeral=True)
            return

        start_date, end_date, _ = year_range

        await ctx.respond(
            f"{year}年度のロール付与を受け付けました",
            ephemeral=True
        )

        count = 0
        for member in guild.members:
            if member.bot:
                continue

            if member.joined_at and start_date <= member.joined_at < end_date:
                if role not in member.roles:
                    await member.add_roles(role)
                count += 1

        await ctx.followup.send(
            f"{year}年度の条件に合うメンバー{count}人に{role_name}を付与しました。",
            ephemeral=True
        )


def setup(bot):
    bot.add_cog(rolecog(bot))
