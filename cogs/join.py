import discord
from discord.ext import commands


CHANNEL_ID = 1430175646381772871


def format_form_answers(answers):
    answer_map = {}
    for item in answers:
        question = str(item.get("question", "")).strip()
        answer = item.get("answer", "")

        if isinstance(answer, list):
            answer = " ".join(str(v).strip() for v in answer if str(v).strip())
        else:
            answer = str(answer).strip()

        answer_map[question] = answer

    handle_name = answer_map.get("ハンドルネームを入力してください", "")
    last_name = answer_map.get("あなたの苗字を入力してください", "")
    last_name_kana = answer_map.get("苗字のフリガナを入力してください", "")
    first_name = answer_map.get("あなたの名前を入力してください", "")
    first_name_kana = answer_map.get("名前のフリガナ入力してください", "")
    waseda_check = answer_map.get("早稲田大学の生徒ですか", "")
    faculty = answer_map.get("学部を教えてください。", "")
    other_university_and_faculty = answer_map.get("大学名と学部を教えてください。", "")
    student_id = answer_map.get("学籍番号を教えてください。", "")
    grade = answer_map.get("学年を教えてください。(2026年度時点）", "")

    lines = []

    if handle_name:
        lines.append("**ハンドルネーム**")
        lines.append(handle_name)
        lines.append("")

    name_line = ""

    if last_name or first_name:
        name_line = f"{last_name}　{first_name}".strip()

    kana_text = ""
    if last_name_kana or first_name_kana:
        kana_text = f"{last_name_kana}　{first_name_kana}".strip()

    if kana_text:
        if name_line:
            name_line = f"{name_line}　({kana_text})"
        else:
            name_line = f"({kana_text})"

    if name_line:
        lines.append("**名前**")
        lines.append(name_line)
        lines.append("")

    university_block = []

    if waseda_check == "はい":
        university_line = "早稲田大学"
        if faculty:
            university_line += f"　{faculty}"
        if grade:
            university_line += f"　{grade}"
        university_block.append(university_line)

        if student_id:
            university_block.append(student_id)

    elif waseda_check == "いいえ":
        university_line = other_university_and_faculty
        if grade:
            university_line += f"　{grade}"
        if university_line:
            university_block.append(university_line)

        if student_id:
            university_block.append(student_id)

    if university_block:
        lines.append("**大学**")
        lines.extend(university_block)

    return "\n".join(lines).strip()


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
        embed.description = format_form_answers(answers)

        view = Button_Call()
        if image_url:
            embed.set_image(url=image_url)

        await channel.send(embed=embed, view=view)


class Button_Call(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="確認", style=discord.ButtonStyle.primary, custom_id="join_confirm_button")
    async def button(self, button: discord.ui.Button, interaction: discord.Interaction):
        await interaction.response.send_modal(Inputname_modal())


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
    bot.add_view(Button_Call())
