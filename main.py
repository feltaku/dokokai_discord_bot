
import discord
from discord.ext import commands
import asyncio

#サーバーのID
#深夜鯖1222402209992671262
#個人鯖1260616353971441694
#同好会1026051164782993478

#botと接続
TOKEN = 'MTM2NzQxNjM5MzkyNjE4NTA1Mg.GVm7JP.PyDo9sPO0OXRMipC3PnsXYg3FRrleduQ2WWZiU'
GUILD = discord.Object(id=int('1026051164782993478'))
intents = discord.Intents.all()

intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)
path = "./cogs"

#botの起動
@bot.event
async def on_ready():
    print(f" {bot.user}がログインしました (ID: {bot.user.id})")
    try:
        synced = await bot.tree.sync()
        print(f" {len(synced)} 個のコマンドを同期しました")
    except Exception as e:
        print(f"Failed to sync commands: {e}")

async def main():
    await bot.load_extension("cogs.role")
    await bot.load_extension("cogs.admin")
    await bot.load_extension("cogs.test")
    await bot.load_extension("cogs.member")

    await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())

