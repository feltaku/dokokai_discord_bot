
import discord
from discord.ext import commands
import asyncio
from aiohttp import web
import os


TOKEN = os.environ.get('TOKEN')
GUILD_ID = 1026051164782993478
intents = discord.Intents.all()

bot = commands.Bot(command_prefix="!", intents=intents)
path = "./cogs"

async def health_check(request):
    return web.Response(text="OK", status=200)

async def handle_webhook(request):
    try:
        data = await request.json()

        await bot.wait_until_ready()

        join_cog = bot.get_cog("JoinCog")
        if join_cog is None:
            return web.Response(text="JoinCog not found", status=500)

        await join_cog.send_form_notification(data)
        return web.Response(text="OK", status=200)

    except Exception as e:
        print(f"Webhook処理中にエラー: {e}")
        return web.Response(text="Error", status=500)
    
async def start_web_server():
    app = web.Application()
    app.router.add_get("/", health_check)
    app.router.add_post("/webhook", handle_webhook)

    runner = web.AppRunner(app)
    await runner.setup()

    port = int(os.environ.get("PORT", 5000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

    print(f"Webhookサーバ起動中 → ポート {port}")


@bot.event
async def on_ready():
    print(f"{bot.user}がログインしました (ID: {bot.user.id})")
    try:
        synced = await bot.sync_commands(guild_ids=[GUILD_ID])

        if synced is None:
            print("コマンド同期は完了しました")
        else:
            print(f"{len(synced)} 個のコマンドを同期しました")

    except Exception as e:
        print(f"Failed to sync commands: {e}")

def load_cogs():
    bot.load_extension("cogs.role")
    bot.load_extension("cogs.admin")
    bot.load_extension("cogs.test")
    bot.load_extension("cogs.member")
    bot.load_extension("cogs.join")
    bot.load_extension("cogs.UID")

async def main():
    load_cogs()
    await start_web_server()
    await bot.start(TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
