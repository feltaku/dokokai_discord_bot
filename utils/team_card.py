from pathlib import Path
from io import BytesIO
from collections import Counter
import itertools
import json

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps, ImageChops


CARD_WIDTH = 1920
CARD_HEIGHT = 480

PROJECT_ROOT = Path(__file__).resolve().parent.parent
IMAGE_BASE = PROJECT_ROOT / "image"

EQUIP_PARTS = ["flower", "wing", "clock", "cup", "crown"]

PART_JA = {
    "flower": "花",
    "wing": "羽",
    "clock": "時計",
    "cup": "杯",
    "crown": "冠",
}

ELEMENT_COLORS = {
    "岩": "#bb9f4b",
    "風": "#52B0B1",
    "氷": "#46A8BA",
    "水": "#84A1C6",
    "雷": "#9876AD",
    "炎": "#BA8C83",
    "草": "#3D9243",
    "なし": "#94a0a7",
}

PERCENT_NAMES = {
    "会心率",
    "会心ダメージ",
    "攻撃パーセンテージ",
    "防御パーセンテージ",
    "HPパーセンテージ",
    "元素チャージ効率",
    "水元素ダメージ",
    "物理ダメージ",
    "風元素ダメージ",
    "岩元素ダメージ",
    "炎元素ダメージ",
    "雷元素ダメージ",
    "氷元素ダメージ",
    "草元素ダメージ",
    "与える治癒効果",
    "与える治療効果",
}

OPTION_DISPLAY = {
    "攻撃パーセンテージ": "攻撃%",
    "防御パーセンテージ": "防御%",
    "HPパーセンテージ": "HP%",
    "元素チャージ効率": "元チャ効率",
    "会心ダメージ": "会心ダメ",
    "草元素ダメージ": "草ダメ",
    "炎元素ダメージ": "炎ダメ",
    "水元素ダメージ": "水ダメ",
    "雷元素ダメージ": "雷ダメ",
    "風元素ダメージ": "風ダメ",
    "岩元素ダメージ": "岩ダメ",
    "氷元素ダメージ": "氷ダメ",
    "物理ダメージ": "物理ダメ",
}

UI_COLORS = {
    "Panel": "#00000050",
    "Dark": "#28282879",
    "TalentBack": "#ffffff66",
    "Green": "#82ff9aff",
    "White": "#ffffffff",
    "WhiteDim": "#ffffffd0",
    "ScoreGray": "#a0a0a0ff",
    "Badge": "#28282880",
    "ScoreBar": "#28282895",
}


def hex_to_rgba(color: str):
    h = color.replace("#", "")
    if len(h) == 6:
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4)) + (255,)
    if len(h) == 8:
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4, 6))
    raise ValueError(f"Invalid color: {color}")


PANEL = hex_to_rgba(UI_COLORS["Panel"])
DARK = hex_to_rgba(UI_COLORS["Dark"])
TALENT_BACK_ALPHA = 150
GREEN = hex_to_rgba(UI_COLORS["Green"])
WHITE = hex_to_rgba(UI_COLORS["White"])
WHITE_DIM = hex_to_rgba(UI_COLORS["WhiteDim"])
SCORE_GRAY = hex_to_rgba(UI_COLORS["ScoreGray"])
BADGE = hex_to_rgba(UI_COLORS["Badge"])
SCORE_BAR = hex_to_rgba(UI_COLORS["ScoreBar"])


def github_url(*parts: str):
    path = IMAGE_BASE
    for p in parts:
        path = path / str(p)
    return path


def open_img(path: Path, mode="RGBA"):
    return Image.open(path).convert(mode)


def open_font(size: int):
    return ImageFont.truetype(str(github_url("Assets", "ja-jp.ttf")), size)


def fit_box(img: Image.Image, w: int, h: int):
    ratio = min(w / img.width, h / img.height)
    return img.resize((int(img.width * ratio), int(img.height * ratio)), Image.Resampling.LANCZOS)


def paste_shadow(base: Image.Image, img: Image.Image, xy, blur=14, offset=(4, 4)):
    x, y = map(int, xy)
    shadow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    alpha = img.getchannel("A").filter(ImageFilter.GaussianBlur(blur))
    shadow.putalpha(alpha)
    base.alpha_composite(shadow, (x + offset[0], y + offset[1]))
    base.alpha_composite(img, (x, y))


def panel(base: Image.Image, box, radius=16, fill=PANEL):
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.rounded_rectangle(tuple(map(int, box)), radius=radius, fill=fill)
    base.alpha_composite(layer)


def rounded_rect(base: Image.Image, box, radius=6, fill=BADGE):
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.rounded_rectangle(tuple(map(int, box)), radius=radius, fill=fill)
    base.alpha_composite(layer)


def bottom_round_bar(base: Image.Image, box, radius=16, fill=DARK):
    x1, y1, x2, y2 = map(int, box)
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.rounded_rectangle((x1, y1, x2, y2), radius=radius, fill=fill)
    d.rectangle((x1, y1, x2, y1 + radius), fill=fill)
    base.alpha_composite(layer)


def text_right(draw: ImageDraw.ImageDraw, xy, text, font, fill=WHITE):
    draw.text(tuple(map(int, xy)), str(text), font=font, fill=fill, anchor="ra")


def text_shadow(draw: ImageDraw.ImageDraw, xy, text, font, fill=WHITE):
    x, y = map(int, xy)
    draw.text((x + 2, y + 2), str(text), font=font, fill=(0, 0, 0, 150))
    draw.text((x, y), str(text), font=font, fill=fill)


def format_value(option: str, value):
    if option in PERCENT_NAMES:
        return f"{float(value)}%"
    if isinstance(value, float) and value.is_integer():
        return format(int(value), ",")
    if isinstance(value, int):
        return format(value, ",")
    return str(value)


def short_option(option: str):
    return OPTION_DISPLAY.get(option, option)


def get_part_score_rank(part: str, score: float):
    point_refer = {
        "flower": {"SS": 50, "S": 45, "A": 40},
        "wing": {"SS": 50, "S": 45, "A": 40},
        "clock": {"SS": 45, "S": 40, "A": 35},
        "cup": {"SS": 45, "S": 40, "A": 37},
        "crown": {"SS": 40, "S": 35, "A": 30},
    }

    if score >= point_refer[part]["SS"]:
        return "SS"
    if score >= point_refer[part]["S"]:
        return "S"
    if score >= point_refer[part]["A"]:
        return "A"
    return "B"


def get_total_score_rank(total_score: float):
    if total_score >= 220:
        return "SS"
    if total_score >= 200:
        return "S"
    if total_score >= 180:
        return "A"
    return "B"


def culculate_op(data: dict):
    dup = json.load(open(github_url("Assets", "duplicate.json"), encoding="utf-8"))
    mapping = json.load(open(github_url("Assets", "subopM.json"), encoding="utf-8"))

    res = [None, None, None, None]
    keymap = list(map(str, data.keys()))

    is_dup = []
    for ctg, state in data.items():
        dup_value = dup[ctg]["ov"]
        if str(state) in dup_value:
            is_dup.append((ctg, state))

    counter_flag = 0
    dup_ctg = [i[0] for i in is_dup]
    maxium_state_ct = 9

    if not len(is_dup):
        for ctg, state in data.items():
            idx = keymap.index(ctg)
            res[idx] = mapping[ctg][str(state)]
        return res

    single_state = {c: s for c, s in data.items() if c not in dup_ctg}
    for ctg, state in single_state.items():
        idx = keymap.index(ctg)
        res[idx] = mapping[ctg][str(state)]
        counter_flag += len(mapping[ctg][str(state)])

    dup_state = {c: s for c, s in data.items() if c in dup_ctg}
    long = maxium_state_ct - counter_flag
    sample = [[ctg, state] for ctg, state in dup_state.items()]

    possibilities = [dup[item[0]][str(item[1])] for item in sample]
    lengths = [[len(p) for p in poss] for poss in possibilities]

    for combo in itertools.product(*lengths):
        if sum(combo) == long or sum(combo) == long - 1:
            for sample_index, length_value in enumerate(combo):
                idx = keymap.index(sample[sample_index][0])
                res[idx] = possibilities[sample_index][lengths[sample_index].index(length_value)]
            return res

    return res


def get_character_folder_name(character_name: str, element: str):
    if character_name in ["蛍", "空", "旅人"]:
        return f"蛍({element})" if character_name in ["蛍", "旅人"] else f"空({element})"
    return character_name


def create_single_team_card(
    data: dict,
    output_path: str | Path = "team_card_test.png",
):
    element = data["元素"]
    character = data["Character"]
    weapon = data["Weapon"]
    artifacts = data["Artifacts"]
    score = data["Score"]

    character_name = character["Name"]
    character_level = character["Level"]
    constellation = character["Const"]
    talents = character["Talent"]
    status = character["Status"]
    base_status = character["Base"]

    weapon_name = weapon["name"]
    weapon_rank = weapon["totu"]

    character_folder = get_character_folder_name(character_name, element)

    f_name = open_font(34)
    f_label = open_font(24)
    f_level = open_font(30)
    f_value = open_font(26)
    f_main = open_font(34)
    f_small = open_font(21)
    f_tiny = open_font(18)
    f_roll = open_font(12)
    f_score = open_font(28)
    f_rank = open_font(34)
    f_footer = open_font(16)

    bg_color = hex_to_rgba(ELEMENT_COLORS.get(element, ELEMENT_COLORS["なし"]))
    card = Image.new("RGBA", (CARD_WIDTH, CARD_HEIGHT), bg_color)

    overlay_path = github_url("team_card", "overlay.jpg")
    if overlay_path.exists():
        overlay = open_img(overlay_path).resize((CARD_WIDTH, CARD_HEIGHT))
        blended = ImageChops.overlay(card.convert("RGB"), overlay.convert("RGB")).convert("RGBA")
        card = Image.blend(card, blended, 0.72)

    draw = ImageDraw.Draw(card)

    root_x = 8
    root_y = 8
    root_w = CARD_WIDTH - 16
    root_h = CARD_HEIGHT - 16

    left_w = int(root_w * 0.23)
    stat_w = int(root_w * 0.27)
    relic_w = int(root_w * 0.10)

    left_x = root_x
    stat_x = left_x + left_w
    relic_start_x = stat_x + stat_w

    stat_inner = (stat_x + 8, root_y + 8, stat_x + stat_w - 8, root_y + root_h - 8)

    # 名前・元素
    element_icon_name = f"{element}元素ダメージ.png"
    element_icon_path = github_url("emotes", element_icon_name)

    if element_icon_path.exists():
        icon = open_img(element_icon_path).resize((42, 42))
        card.alpha_composite(icon, (left_x + 10, root_y + 10))

    text_shadow(draw, (left_x + 60, root_y + 14), character_name, f_name)

    # 天賦
    talent_back_path = github_url("Assets", "TalentBack.png")
    talent_back = open_img(talent_back_path) if talent_back_path.exists() else None

    skill_x = left_x + 42
    skill_y0 = root_y + 78

    for i, key in enumerate(["通常", "スキル", "爆発"]):
        tx = skill_x
        ty = skill_y0 + i * 80

        if talent_back:
            back = talent_back.copy()

            # UID.py と同じく元画像の透過を壊さず 1/1.5 に縮小
            back = back.resize(
                (int(back.width / 1.5), int(back.height / 1.5)),
                Image.Resampling.LANCZOS
            )

            card.alpha_composite(back, (tx - 16, ty - 10))

        talent_path = github_url("character", character_folder, f"{key}.png")
        if talent_path.exists():
            talent_img = open_img(talent_path).resize((60, 60))
            card.alpha_composite(talent_img, (tx + 3, ty + 3))
            
        lv = talents.get(key, 1)
        rounded_rect(card, (tx + 42, ty + 38, tx + 88, ty + 76), radius=6, fill=BADGE)
        draw.text(
            (tx + 65, ty + 44),
            str(lv),
            font=f_tiny,
            fill=(0, 255, 255, 255) if lv >= 10 else WHITE,
            anchor="ma"
        )

    # 横顔
    side_path = github_url("character", character_folder, "side.png")
    if side_path.exists():
        side = fit_box(open_img(side_path), 240, 240)
        card.alpha_composite(side, (left_x + 135, root_y + 20))

    text_shadow(draw, (left_x + 220, root_y + 280), f"Lv.{character_level}", f_level)

    # 凸：縦配置
    const_size = 70
    const_icon_size = 30
    const_gap = 64

    # 数値を小さくすると右へ、大きくすると左へ
    const_x = left_x + left_w - 60
    const_y0 = root_y + 44

    const_positions = [
        (const_x, const_y0 + const_gap * i)
        for i in range(6)
    ]

    const_frame_path = github_url("命の星座", f"{element}.png")
    const_lock_path = github_url("命の星座", f"{element}LOCK.png")

    const_frame = open_img(const_frame_path) if const_frame_path.exists() else None
    const_lock = open_img(const_lock_path) if const_lock_path.exists() else None

    for i in range(6):
        const_x_i, const_y_i = const_positions[i]
        unlocked = i < constellation

        if unlocked and const_frame:
            frame = const_frame.resize((const_size, const_size), Image.Resampling.LANCZOS)
            card.alpha_composite(frame, (const_x_i, const_y_i))

            const_path = github_url("character", character_folder, f"{i + 1}.png")
            if const_path.exists():
                const_img = open_img(const_path).resize(
                    (const_icon_size, const_icon_size),
                    Image.Resampling.LANCZOS
                )

                icon_x = const_x_i + (const_size - const_icon_size) // 2
                icon_y = const_y_i + (const_size - const_icon_size) // 2

                # 凸アイコンだけ少し右へ
                icon_x -= 2
                icon_y -= 1

                card.alpha_composite(const_img, (icon_x, icon_y))

        elif const_lock:
            lock = const_lock.resize((const_size, const_size), Image.Resampling.LANCZOS)
            card.alpha_composite(lock, (const_x_i, const_y_i))

    # 武器
    weapon_path = github_url("weapon", f"{weapon_name}.png")
    if weapon_path.exists():
        weapon_img = fit_box(open_img(weapon_path), 112, 112)
        card.alpha_composite(weapon_img, (left_x + 64, root_y + 330))
        rounded_rect(card, (left_x + 128, root_y + 412, left_x + 174, root_y + 450), radius=6, fill=BADGE)
        draw.text((left_x + 151, root_y + 418), f"R{weapon_rank}", font=f_tiny, fill=WHITE, anchor="ma")

    dokokai_icon_path = github_url("dokokai_icon.png")
    if dokokai_icon_path.exists():
        dokokai_icon = open_img(dokokai_icon_path)
        dokokai_icon = ImageOps.fit(
            dokokai_icon,
            (40, 40),
            method=Image.Resampling.LANCZOS
        )
        card.alpha_composite(dokokai_icon, (left_x + 14, root_y + 430))

    # セット表示
    set_counter = Counter()
    for part in EQUIP_PARTS:
        art = artifacts.get(part)
        if art:
            set_counter[art["type"]] += 1

    active_sets = [(name, count) for name, count in set_counter.items() if count >= 2]

    # 4セットなら1つだけ表示
    if len(active_sets) == 1 and active_sets[0][1] >= 4:
        set_name, set_count = active_sets[0]

        set_icon_path = github_url("Artifact", set_name, "flower.png")
        if set_icon_path.exists():
            set_img = fit_box(open_img(set_icon_path), 112, 112)
            card.alpha_composite(set_img, (left_x + 248, root_y + 330))

        rounded_rect(card, (left_x + 326, root_y + 412, left_x + 372, root_y + 450), radius=6, fill=BADGE)
        draw.text((left_x + 349, root_y + 418), "4", font=f_tiny, fill=WHITE, anchor="ma")

    # 2セット複合なら2つ表示
    elif len(active_sets) >= 2:
        display_sets = active_sets[:2]

        set_positions = [
            {
                "img": (left_x + 218, root_y + 338),
                "badge": (left_x + 272, root_y + 412, left_x + 318, root_y + 450),
                "text": (left_x + 295, root_y + 418),
            },
            {
                "img": (left_x + 288, root_y + 338),
                "badge": (left_x + 342, root_y + 412, left_x + 388, root_y + 450),
                "text": (left_x + 365, root_y + 418),
            },
        ]

        for set_index, (set_name, set_count) in enumerate(display_sets):
            pos = set_positions[set_index]

            set_icon_path = github_url("Artifact", set_name, "flower.png")
            if set_icon_path.exists():
                set_img = fit_box(open_img(set_icon_path), 92, 92)
                card.alpha_composite(set_img, pos["img"])

            rounded_rect(card, pos["badge"], radius=6, fill=BADGE)
            draw.text(pos["text"], "2", font=f_tiny, fill=WHITE, anchor="ma")

    draw.text((left_x + 180, root_y + 450), "ﾄﾞｺｶｲArtifacter", font=f_footer, fill=WHITE)


    # ステータス欄
    panel(card, stat_inner)

    state_order = ["HP", "攻撃力", "防御力", "元素熟知", "会心率", "会心ダメージ", "元素チャージ効率"]
    element_stat = next((k for k in status.keys() if k.endswith("元素ダメージ") or k == "物理ダメージ"), None)
    if element_stat:
        state_order.append(element_stat)

    stat_x_text = stat_inner[0] + 72
    stat_icon_x = stat_inner[0] + 24
    stat_right = stat_inner[2] - 28
    y = stat_inner[1] + 24

    for key in state_order:
        if key not in status:
            continue

        value = status[key]

        icon_path = github_url("emotes", f"{key}.png")
        if icon_path.exists():
            icon = open_img(icon_path).resize((34, 34))
            card.alpha_composite(icon, (stat_icon_x, y - 2))

        draw.text((stat_x_text, y), key, font=f_label, fill=WHITE)

        value_text = format_value(key, value)
        text_right(draw, (stat_right, y), value_text, f_label)

        if key in ["HP", "攻撃力", "防御力"]:
            base_value = base_status.get(key, 0)
            plus_value = int(value) - int(base_value)
            plus_text = f"+{format(plus_value, ',')}"
            base_text = format(base_value, ",")

            plus_len = draw.textlength(plus_text, font=f_tiny)
            base_len = draw.textlength(base_text, font=f_tiny)

            base_plus_text = f"{base_text} {plus_text}"

            base_plus_right = stat_right - 120

            plus_width = draw.textlength(plus_text, font=f_tiny)
            base_width = draw.textlength(base_text, font=f_tiny)

            # 基礎値（白）
            draw.text(
                (
                    base_plus_right - plus_width - base_width - 4,
                    y + 2
                ),
                base_text,
                font=f_tiny,
                fill=WHITE_DIM
            )

            # 加算値（緑）
            draw.text(
                (
                    base_plus_right - plus_width,
                    y + 2
                ),
                plus_text,
                font=f_tiny,
                fill=GREEN
            )

        y += 52

    # 聖遺物5枠
    for i, part in enumerate(EQUIP_PARTS):
        art = artifacts.get(part)

        col_x = relic_start_x + i * relic_w
        box = (col_x + 8, root_y + 8, col_x + relic_w - 8, root_y + root_h - 42)
        panel(card, box)

        ox1, oy1, ox2, oy2 = map(int, box)

        if not art:
            bottom_h = 52
            bottom_y = oy2 - bottom_h
            bottom_round_bar(card, (ox1, bottom_y, ox2, oy2), radius=16, fill=SCORE_BAR)

            continue

        ox1, oy1, ox2, oy2 = map(int, box)

        art_img_path = github_url("Artifact", art["type"], f"{part}.png")
        if art_img_path.exists():
            preview = open_img(art_img_path).resize((256, 256))
            preview = fit_box(preview, 155, 155)
            card.alpha_composite(preview, (ox1 - 2, oy1 - 2))

        main = art["main"]
        main_option = main["option"]
        main_value = main["value"]

        main_icon_path = github_url("emotes", f"{main_option}.png")

        if main_icon_path.exists():
            main_icon = open_img(main_icon_path).resize((38, 38))
            card.alpha_composite(main_icon, (ox2 - 52, oy1 + 112))
        text_right(draw, (ox2 - 16, oy1 + 145), format_value(main_option, main_value), f_main)

        psb = None
        if art["Level"] == 20 and art["rarelity"] == 5:
            c_data = {}
            for sub in art["sub"]:
                if sub["option"] in PERCENT_NAMES:
                    c_data[sub["option"]] = str(float(sub["value"]))
                else:
                    c_data[sub["option"]] = str(sub["value"])
            psb = culculate_op(c_data)

        sub_y = oy1 + 200
        row_h = 42

        for sub_index, sub in enumerate(art["sub"][:4]):
            sub_option = sub["option"]
            sub_value = sub["value"]

            sub_icon_path = github_url("emotes", f"{sub_option}.png")
            if sub_icon_path.exists():
                sub_icon = open_img(sub_icon_path).resize((26, 26))
                card.alpha_composite(sub_icon, (ox1 + 18, sub_y - 1))

            text_color = WHITE_DIM if sub_option in ["HP", "攻撃力", "防御力"] else WHITE
            sub_text = format_value(sub_option, sub_value)
            text_right(draw, (ox2 - 18, sub_y), sub_text, f_tiny, fill=text_color)

            if psb is not None and sub_index < len(psb) and psb[sub_index] is not None:
                nobi_text = "+".join(map(str, psb[sub_index]))
                nobi_len = draw.textlength(nobi_text, font=f_roll)
                draw.text((ox2 - nobi_len - 18, sub_y + 20), nobi_text, font=f_roll, fill=WHITE_DIM)

            sub_y += row_h


        # 下バー
        bottom_h = 52
        bottom_y = oy2 - bottom_h
        bottom_round_bar(card, (ox1, bottom_y, ox2, oy2), radius=16, fill=SCORE_BAR)

        part_score = float(score.get(part, 0))
        rank = get_part_score_rank(part, part_score)

        # スコア
        part_score = float(score.get(part, 0))
        score_y = bottom_y + 10
        text_right(draw, (ox2 - 18, score_y), part_score, f_score, fill=WHITE)

        part_score = float(score.get(part, 0))
        rank = get_part_score_rank(part, part_score)

        rank_path = github_url("artifactGrades", f"{rank}.png")

        if rank_path.exists():
            rank_img = open_img(rank_path)
            rank_img = fit_box(rank_img, 44, 34)

            rank_x = ox1 + 18
            rank_y = bottom_y + (bottom_h - rank_img.height) // 2

            card.alpha_composite(rank_img, (rank_x, rank_y))
        else:
            draw.text(
                (ox1 + 24, bottom_y + bottom_h // 2),
                rank,
                font=f_tiny,
                fill=WHITE,
                anchor="lm",
            )

        total_score = float(score.get("total", 0))
        total_rank = get_total_score_rank(total_score)

        total_score_text = f'{score.get("State", "")}換算　総合スコア{total_score}'
        total_score_len = draw.textlength(total_score_text, font=f_label)

        text_x = CARD_WIDTH - total_score_len - 320
        text_y = CARD_HEIGHT - 34

        draw.text(
            (text_x, text_y),
            total_score_text,
            font=f_label,
            fill=WHITE,
        )

        rank_path = github_url("artifactGrades", f"{total_rank}.png")
        if rank_path.exists():
            rank_img = open_img(rank_path)
            rank_img = fit_box(rank_img, 58, 42)
            card.alpha_composite(rank_img, (CARD_WIDTH - 310, CARD_HEIGHT - 46))
        else:
            draw.text(
                (CARD_WIDTH - 70, CARD_HEIGHT - 38),
                total_rank,
                font=f_label,
                fill=WHITE,
            )

    output_path = Path(output_path)
    card.save(output_path)
    return output_path


def create_team_card(
    team_data: list[dict],
    output_path: str | Path | None = None,
):
    temp_dir = PROJECT_ROOT / "tmp"
    temp_dir.mkdir(exist_ok=True)

    card_paths = []

    for i, data in enumerate(team_data):
        card_path = temp_dir / f"team_card_part_{i + 1}.png"
        create_single_team_card(
            data=data,
            output_path=card_path
        )
        card_paths.append(card_path)

    images = [Image.open(path).convert("RGBA") for path in card_paths]

    total_width = CARD_WIDTH
    total_height = CARD_HEIGHT * len(images)

    result = Image.new("RGBA", (total_width, total_height), (0, 0, 0, 0))

    y = 0
    for img in images:
        result.alpha_composite(img, (0, y))
        y += CARD_HEIGHT

    if output_path is not None:
        output_path = Path(output_path)
        result.save(output_path)
        return output_path

    buffer = BytesIO()
    result.save(buffer, format="PNG")
    buffer.seek(0)

    for img in images:
        img.close()

    return buffer