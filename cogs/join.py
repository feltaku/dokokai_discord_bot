import discord
from discord.ext import commands

CHANNEL_ID = 1367572896821805066  # 送信先チャンネル

class JoinCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def send_form_notification(self, data):
        channel = self.bot.get_channel(CHANNEL_ID)
        if not channel:
            raise RuntimeError("Channel not found")

        answers = data.get("answers", [])
        image_url = data.get("image")

        embed = discord.Embed(title="フォーム提出通知")
        text = ""
        for item in answers:
            text += f"**{item['question']}**\n{item['answer']}\n\n"
        embed.description = text

        view = None
        if image_url:
            embed.set_image(url=image_url)
            view = Button_Call()

        await channel.send(embed=embed, view=view)

#モーダルを呼ぶボタン
class Button_Call(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label='確認', style=discord.ButtonStyle.primary)
    async def button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(Inputname_modal())

#モーダル
class Inputname_modal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="入会者の名前")

        self.comment = discord.ui.InputText(
            label="入会者の名前を入力してね",
            placeholder="例:ふぇると",
            required=True
        )

        self.add_item(self.comment)

    async def callback(self, interaction: discord.Interaction):
        display = interaction.user.display_name
        username = interaction.user.name

        await interaction.response.edit_message(
            content=f"**{self.comment.value}**\n{display}({username})が確認しました",
            embed=None,
            view=None
        )
        
def setup(bot):
    bot.add_cog(JoinCog(bot))
