import discord
from discord.ext import commands
from flask import Flask, request, jsonify
import threading
import datetime
import asyncio
import os

CHANNEL_ID = 1430175646381772871  # Discord通知先チャンネルID

class JoinCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.app = Flask(__name__)
        self.setup_routes()
        threading.Thread(target=self.run_flask).start()

    def setup_routes(self):
        @self.app.route("/", methods=["GET"])
        def health():
            return "Bot is alive", 200

        @self.app.route("/webhook", methods=["POST"])
        def webhook():
            data = request.json
            answers = data.get("answers", [])
            image_url = data.get("image")

            # Embed作成
            embed = discord.Embed(
                title="フォームが送信されました",
                description=f"送信時刻: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                color=0x2b6cb0
            )

            for entry in answers:
                question = entry.get("question", "不明な質問")
                answer = entry.get("answer", "未回答")
                if len(str(answer)) > 1024:
                    answer = str(answer)[:1021] + "..."
                embed.add_field(name=question, value=answer, inline=False)

            if image_url:
                embed.set_image(url=image_url)

            embed.set_footer(text="自動送信: Googleフォーム連携BOT")

            view = Button_Call()
            
            async def send_embed():
                channel = self.bot.get_channel(CHANNEL_ID)
                if channel:
                    await channel.send(embed=embed, view=view)
                else:
                    print(f"チャンネルID {CHANNEL_ID} が見つかりません")

            asyncio.run_coroutine_threadsafe(send_embed(), self.bot.loop)
            return jsonify({"status": "success"}), 200

    def run_flask(self):
        port = int(os.environ.get("PORT", 8080))  # ← Koyebが指定するPORTを使用
        print(f"Flask webhook server running on port {port}")
        self.app.run(host="0.0.0.0", port=port)

#モーダルを呼ぶボタン
class Button_Call(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label='確認', style=discord.ButtonStyle.primary)
    async def button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(Inputname_modal())

#モーダル
class Inputname_modal(discord.ui.Modal, title="入会者の名前"):
    comment = discord.ui.TextInput(
        label="入会者の名前を入力してね",
        placeholder="例:ふぇると",
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        editer = interaction.user.display_name
        await interaction.response.edit_message(
            content=f"**{self.comment.value}**\n{editer}が確認しました",
            embed=None,
            view=None
        )

async def setup(bot):
    await bot.add_cog(JoinCog(bot))
