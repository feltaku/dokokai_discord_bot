import base64
import itertools
import json
import time
from collections import Counter
from io import BytesIO
from pathlib import Path

import discord
import requests
from discord.ext import commands
from PIL import Image, ImageDraw, ImageEnhance, ImageFile, ImageFont, ImageOps

ImageFile.LOAD_TRUNCATED_IMAGES = True


# ====パス設定====

PROJECT_ROOT = Path(__file__).resolve().parent.parent
IMAGE_BASE = PROJECT_ROOT / "image"

CHARACTERS_JSON_URL = PROJECT_ROOT / "characters.json"
LOC_JSON_URL = PROJECT_ROOT / "loc.json"

HTTP = requests.Session()
_JSON_CACHE = {}
_IMAGE_CACHE = {}
_FONT_CACHE = {}

# ====マッピング====

EQUIP_SLOT_MAP = {
    "EQUIP_BRACER": "flower",
    "EQUIP_NECKLACE": "wing",
    "EQUIP_SHOES": "clock",
    "EQUIP_RING": "cup",
    "EQUIP_DRESS": "crown",
}

ELEMENT_PROP_CANDIDATES = [
    ("草元素ダメージ", "FIGHT_PROP_GRASS_ADD_HURT", 43),
    ("炎元素ダメージ", "FIGHT_PROP_FIRE_ADD_HURT", 40),
    ("水元素ダメージ", "FIGHT_PROP_WATER_ADD_HURT", 42),
    ("雷元素ダメージ", "FIGHT_PROP_ELEC_ADD_HURT", 41),
    ("風元素ダメージ", "FIGHT_PROP_WIND_ADD_HURT", 44),
    ("岩元素ダメージ", "FIGHT_PROP_ROCK_ADD_HURT", 45),
    ("氷元素ダメージ", "FIGHT_PROP_ICE_ADD_HURT", 46),
    ("物理ダメージ", "FIGHT_PROP_PHYSICAL_ADD_HURT", 30),
]

PERCENT_PROP_IDS = {
    "FIGHT_PROP_HP_PERCENT",
    "FIGHT_PROP_ATTACK_PERCENT",
    "FIGHT_PROP_DEFENSE_PERCENT",
    "FIGHT_PROP_CRITICAL",
    "FIGHT_PROP_CRITICAL_HURT",
    "FIGHT_PROP_CHARGE_EFFICIENCY",
    "FIGHT_PROP_HEAL_ADD",
    "FIGHT_PROP_HEALED_ADD",
    "FIGHT_PROP_PHYSICAL_ADD_HURT",
    "FIGHT_PROP_FIRE_ADD_HURT",
    "FIGHT_PROP_ELEC_ADD_HURT",
    "FIGHT_PROP_WATER_ADD_HURT",
    "FIGHT_PROP_GRASS_ADD_HURT",
    "FIGHT_PROP_WIND_ADD_HURT",
    "FIGHT_PROP_ROCK_ADD_HURT",
    "FIGHT_PROP_ICE_ADD_HURT",
}

PROP_ID_TO_JP = {
    "FIGHT_PROP_HP": "HP",
    "FIGHT_PROP_HP_PERCENT": "HPパーセンテージ",
    "FIGHT_PROP_ATTACK": "攻撃力",
    "FIGHT_PROP_ATTACK_PERCENT": "攻撃パーセンテージ",
    "FIGHT_PROP_DEFENSE": "防御力",
    "FIGHT_PROP_DEFENSE_PERCENT": "防御パーセンテージ",
    "FIGHT_PROP_ELEMENT_MASTERY": "元素熟知",
    "FIGHT_PROP_CHARGE_EFFICIENCY": "元素チャージ効率",
    "FIGHT_PROP_CRITICAL": "会心率",
    "FIGHT_PROP_CRITICAL_HURT": "会心ダメージ",
    "FIGHT_PROP_HEAL_ADD": "与える治癒効果",
    "FIGHT_PROP_HEALED_ADD": "与える治療効果",
    "FIGHT_PROP_PHYSICAL_ADD_HURT": "物理ダメージ",
    "FIGHT_PROP_FIRE_ADD_HURT": "炎元素ダメージ",
    "FIGHT_PROP_ELEC_ADD_HURT": "雷元素ダメージ",
    "FIGHT_PROP_WATER_ADD_HURT": "水元素ダメージ",
    "FIGHT_PROP_GRASS_ADD_HURT": "草元素ダメージ",
    "FIGHT_PROP_WIND_ADD_HURT": "風元素ダメージ",
    "FIGHT_PROP_ROCK_ADD_HURT": "岩元素ダメージ",
    "FIGHT_PROP_ICE_ADD_HURT": "氷元素ダメージ",
}

FIGHT_PROP_KEY_ID = {
    "HP": 2000,
    "攻撃力": 2001,
    "防御力": 2002,
    "元素熟知": 28,
    "会心率": 20,
    "会心ダメージ": 22,
    "元素チャージ効率": 23,
    "物理ダメージ": 30,
    "炎元素ダメージ": 40,
    "雷元素ダメージ": 41,
    "水元素ダメージ": 42,
    "草元素ダメージ": 43,
    "風元素ダメージ": 44,
    "岩元素ダメージ": 45,
    "氷元素ダメージ": 46,
}

BASE_FIGHT_PROP_KEY_ID = {
    "HP": 1,
    "攻撃力": 4,
    "防御力": 7,
}

SCORE_MODE_LABELS = {
    "atk": "攻撃",
    "def": "防御",
    "def08": "防御(×0.8)",
    "hp": "HP",
    "er": "元素チャージ",
    "em": "元素熟知",
}

def clear_image_cache():
    _IMAGE_CACHE.clear()

# ====JSON 読み込み====

def load_json(path):
    cache_key = str(path)
    if cache_key in _JSON_CACHE:
        return _JSON_CACHE[cache_key]

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    _JSON_CACHE[cache_key] = data
    return data

def github_url(*parts: str):
    path = IMAGE_BASE
    for p in parts:
        path = path / str(p)
    return path

def open_image_url(
    path,
    convert_mode: str | None = None,
    *,
    use_cache: bool = True,
    cache_max_pixels: int = 300_000
):
    cache_key = (str(path), convert_mode)

    if use_cache and cache_key in _IMAGE_CACHE:
        return _IMAGE_CACHE[cache_key].copy()

    with Image.open(path) as im:
        if convert_mode:
            img = im.convert(convert_mode)
        else:
            img = im.copy()

    if use_cache and (img.width * img.height) <= cache_max_pixels:
        _IMAGE_CACHE[cache_key] = img.copy()

    return img


def open_font_url(path, size: int):
    cache_key = (str(path), size)

    if cache_key in _FONT_CACHE:
        return _FONT_CACHE[cache_key]

    font = ImageFont.truetype(str(path), size)
    _FONT_CACHE[cache_key] = font
    return font

def culculate_op(data: dict):
    dup = load_json(github_url("Assets", "duplicate.json"))
    mapping = load_json(github_url("Assets", "subopM.json"))

    res = [None, None, None, None]
    keymap = list(map(str, data.keys()))

    is_dup = []
    for ctg, state in data.items():
        dup_value = dup[ctg]['ov']
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

    if len(is_dup) == 1:
        single_state = {c: s for c, s in data.items() if c not in dup_ctg}
        for ctg, state in single_state.items():
            idx = keymap.index(ctg)
            res[idx] = mapping[ctg][str(state)]
            counter_flag += len(mapping[ctg][str(state)])

        dup_state = {c: s for c, s in data.items() if c in dup_ctg}
        long = maxium_state_ct - counter_flag

        for ctg, state in dup_state.items():
            possiblity = dup[ctg][str(state)]
            for p in possiblity:
                if len(p) == long or len(p) == long - 1:
                    idx = keymap.index(ctg)
                    res[idx] = p
                    return res

    if len(is_dup) == 2:
        single_state = {c: s for c, s in data.items() if c not in dup_ctg}
        for ctg, state in single_state.items():
            idx = keymap.index(ctg)
            res[idx] = mapping[ctg][str(state)]
            counter_flag += len(mapping[ctg][str(state)])

        dup_state = {c: s for c, s in data.items() if c in dup_ctg}
        long = maxium_state_ct - counter_flag

        sample = [[ctg, state] for ctg, state in dup_state.items()]
        possiblity1 = dup[sample[0][0]][str(sample[0][1])]
        possiblity2 = dup[sample[1][0]][str(sample[1][1])]

        p1 = [len(p) for p in possiblity1]
        p2 = [len(p) for p in possiblity2]

        p = itertools.product(p1, p2)
        for v in p:
            if sum(v) == long or sum(v) == long - 1:
                idx1 = keymap.index(sample[0][0])
                idx2 = keymap.index(sample[1][0])
                res[idx1] = possiblity1[p1.index(v[0])]
                res[idx2] = possiblity2[p2.index(v[1])]
                return res

    if len(is_dup) == 3:
        single_state = {c: s for c, s in data.items() if c not in dup_ctg}
        for ctg, state in single_state.items():
            idx = keymap.index(ctg)
            res[idx] = mapping[ctg][str(state)]
            counter_flag += len(mapping[ctg][str(state)])

        dup_state = {c: s for c, s in data.items() if c in dup_ctg}
        long = maxium_state_ct - counter_flag

        sample = [[ctg, state] for ctg, state in dup_state.items()]
        possiblity1 = dup[sample[0][0]][str(sample[0][1])]
        possiblity2 = dup[sample[1][0]][str(sample[1][1])]
        possiblity3 = dup[sample[2][0]][str(sample[2][1])]

        p1 = [len(p) for p in possiblity1]
        p2 = [len(p) for p in possiblity2]
        p3 = [len(p) for p in possiblity3]

        p = itertools.product(p1, p2, p3)
        for v in p:
            if sum(v) == long or sum(v) == long - 1:
                idx1 = keymap.index(sample[0][0])
                idx2 = keymap.index(sample[1][0])
                idx3 = keymap.index(sample[2][0])
                res[idx1] = possiblity1[p1.index(v[0])]
                res[idx2] = possiblity2[p2.index(v[1])]
                res[idx3] = possiblity3[p3.index(v[2])]
                return res

    if len(is_dup) == 4:
        dup_state = {c: s for c, s in data.items() if c in dup_ctg}
        long = maxium_state_ct - counter_flag

        sample = [[ctg, state] for ctg, state in dup_state.items()]
        possiblity1 = dup[sample[0][0]][str(sample[0][1])]
        possiblity2 = dup[sample[1][0]][str(sample[1][1])]
        possiblity3 = dup[sample[2][0]][str(sample[2][1])]
        possiblity4 = dup[sample[3][0]][str(sample[3][1])]

        p1 = [len(p) for p in possiblity1]
        p2 = [len(p) for p in possiblity2]
        p3 = [len(p) for p in possiblity3]
        p4 = [len(p) for p in possiblity4]

        p = itertools.product(p1, p2, p3, p4)
        for v in p:
            if sum(v) == long or sum(v) == long - 1:
                idx1 = keymap.index(sample[0][0])
                idx2 = keymap.index(sample[1][0])
                idx3 = keymap.index(sample[2][0])
                idx4 = keymap.index(sample[3][0])

                res[idx1] = possiblity1[p1.index(v[0])]
                res[idx2] = possiblity2[p2.index(v[1])]
                res[idx3] = possiblity3[p3.index(v[2])]
                res[idx4] = possiblity4[p4.index(v[3])]
                return res

    return res


def pil_to_bytes(img, format="PNG"):
    buffer = BytesIO()
    img.save(buffer, format)
    buffer.seek(0)
    return buffer


# ====ローカライズ・取得補助====

def get_localized_text(loc_data: dict, text_hash, lang="ja"):
    if text_hash is None:
        return None

    base_hash = str(text_hash)

    def lookup_one(hash_str: str):
        if lang in loc_data and isinstance(loc_data[lang], dict):
            v = loc_data[lang].get(hash_str)
            if v:
                return v

        for alt_lang in ("jp", "ja-jp", "ja_JP", "Japanese"):
            if alt_lang in loc_data and isinstance(loc_data[alt_lang], dict):
                v = loc_data[alt_lang].get(hash_str)
                if v:
                    return v

        if hash_str in loc_data and isinstance(loc_data[hash_str], dict):
            for key in (lang, "jp", "ja-jp", "ja_JP", "Japanese"):
                v = loc_data[hash_str].get(key)
                if v:
                    return v

        return None

    v = lookup_one(base_hash)
    if v:
        return v

    # v6.5 以降のハッシュずれ対策
    # 旧 loc.json しかない環境向けに ±512 を試す
    try:
        n = int(base_hash)
    except (TypeError, ValueError):
        return None

    for diff in (-512, 512):
        shifted = str(n + diff)
        v = lookup_one(shifted)
        if v:
            return v

    return None

def get_character_name(char, characters_data, loc_data):
    avatar_id = str(char["avatarId"])
    meta = characters_data.get(avatar_id, {})
    name_hash = meta.get("NameTextMapHash")
    return get_localized_text(loc_data, name_hash, "ja") or f"不明キャラ({avatar_id})"


def get_profile_icon_url(player_info, characters_data):
    profile_picture = player_info.get("profilePicture", {})
    avatar_id = profile_picture.get("avatarId")
    if avatar_id is None:
        return None

    meta = characters_data.get(str(avatar_id), {})
    side_icon_name = meta.get("SideIconName")
    if not side_icon_name:
        return None

    return f"https://enka.network/ui/{side_icon_name}.png"


def get_weapon_info(char, loc_data):
    for equip in char.get("equipList", []):
        if "weapon" not in equip:
            continue

        flat = equip.get("flat", {})
        weapon_data = equip.get("weapon", {})

        name_hash = flat.get("nameTextMapHash")
        weapon_name = get_localized_text(loc_data, name_hash, "ja") or "不明武器"
        weapon_level = int(weapon_data.get("level", 1))
        rank_level = int(flat.get("rankLevel", 1))

        affix_map = weapon_data.get("affixMap", {})
        refine = 1
        if affix_map:
            try:
                refine = max(int(v) for v in affix_map.values()) + 1
            except Exception:
                refine = 1

        base_atk = 0
        sub_name = None
        sub_value = None

        for stat in flat.get("weaponStats", []):
            append_prop_id = stat.get("appendPropId")
            stat_value = stat.get("statValue")

            if append_prop_id == "FIGHT_PROP_BASE_ATTACK":
                base_atk = int(float(stat_value))
            else:
                sub_name = PROP_ID_TO_JP.get(append_prop_id)
                if append_prop_id in PERCENT_PROP_IDS:
                    sub_value = round(float(stat_value), 1)
                else:
                    sub_value = int(float(stat_value)) if float(stat_value).is_integer() else round(float(stat_value), 1)

        return {
            "name": weapon_name,
            "Level": weapon_level,
            "totu": refine,
            "rarelity": rank_level,
            "BaseATK": base_atk,
            "Sub": {
                "name": sub_name,
                "value": sub_value
            } if sub_name is not None else None
        }

    return {
        "name": "不明武器",
        "Level": 1,
        "totu": 1,
        "rarelity": 1,
        "BaseATK": 0,
        "Sub": None
    }


def get_talent_levels(char, characters_data):
    avatar_id = str(char["avatarId"])

    # 旅人は avatarId-skillDepotId 形式で引く
    if avatar_id in ("10000005", "10000007"):
        skill_depot_id = char.get("skillDepotId")
        traveler_key = f"{avatar_id}-{skill_depot_id}" if skill_depot_id is not None else avatar_id
        char_meta = characters_data.get(traveler_key, characters_data.get(avatar_id, {}))
    else:
        char_meta = characters_data.get(avatar_id, {})

    skill_order = char_meta.get("SkillOrder", [])
    proud_map = char_meta.get("ProudMap", {})
    skill_level_map = char.get("skillLevelMap", {})
    proud_skill_extra_level_map = char.get("proudSkillExtraLevelMap", {})

    talent_results = []

    for index in range(3):
        if index >= len(skill_order):
            talent_results.append(1)
            continue

        skill_id = skill_order[index]
        skill_id_str = str(skill_id)

        base_level = int(skill_level_map.get(skill_id_str, 1))

        proud_id = proud_map.get(skill_id_str)
        if proud_id is None:
            proud_id = proud_map.get(skill_id)

        extra_level = 0
        if proud_id is not None:
            extra_level = int(proud_skill_extra_level_map.get(str(proud_id), 0))

        talent_results.append(base_level + extra_level)

    return {
        "通常": talent_results[0],
        "スキル": talent_results[1],
        "爆発": talent_results[2]
    }


def get_status_value(fight_prop_map: dict, key_name: str):
    prop_id = FIGHT_PROP_KEY_ID[key_name]
    value = fight_prop_map.get(str(prop_id), fight_prop_map.get(prop_id, 0))
    return float(value)


def get_base_status_value(fight_prop_map: dict, key_name: str):
    prop_id = BASE_FIGHT_PROP_KEY_ID[key_name]
    value = fight_prop_map.get(str(prop_id), fight_prop_map.get(prop_id, 0))
    return float(value)


def get_element_name_from_char(char, characters_data):
    avatar_id = str(char["avatarId"])

    # 旅人だけは skillDepotId を優先
    if avatar_id in ("10000005", "10000007"):
        depot_id = char.get("skillDepotId")

        depot_map = {
            701: "Wind",
            702: "Fire",
            703: "Electric",
            704: "Grass",
            705: "Water",
            706: "Rock",
        }

        element_code = depot_map.get(depot_id)
    else:
        char_meta = characters_data.get(avatar_id, {})
        element_code = char_meta.get("Element")

    element_map = {
        "Fire": "炎元素ダメージ",
        "Electric": "雷元素ダメージ",
        "Water": "水元素ダメージ",
        "Wind": "風元素ダメージ",
        "Rock": "岩元素ダメージ",
        "Ice": "氷元素ダメージ",
        "Grass": "草元素ダメージ",
    }

    if element_code in element_map:
        return element_map[element_code]

    fight_prop_map = char.get("fightPropMap", {})
    best_name = "草元素ダメージ"
    best_value = -999.0

    for jp_name, _, prop_id in ELEMENT_PROP_CANDIDATES:
        value = float(fight_prop_map.get(str(prop_id), fight_prop_map.get(prop_id, 0)))
        if value > best_value:
            best_value = value
            best_name = jp_name

    return best_name

def artifact_score_value_from_sub(sub_name: str, sub_value: float, score_mode: str):
    if sub_name == "会心率":
        return sub_value * 2
    if sub_name == "会心ダメージ":
        return sub_value
    if score_mode == "atk" and sub_name == "攻撃パーセンテージ":
        return sub_value
    if score_mode == "def" and sub_name == "防御パーセンテージ":
        return sub_value
    if score_mode == "def08" and sub_name == "防御パーセンテージ":
        return sub_value * 0.8
    if score_mode == "hp" and sub_name == "HPパーセンテージ":
        return sub_value
    if score_mode == "er" and sub_name == "元素チャージ効率":
        return sub_value
    if score_mode == "em" and sub_name == "元素熟知":
        return sub_value / 4
    return 0.0


def calculate_artifact_score(subs: list, score_mode: str):
    total = 0.0
    for sub in subs:
        total += artifact_score_value_from_sub(sub["option"], float(sub["value"]), score_mode)
    return round(total, 1)


def get_score_label_for_display(score_mode: str):
    return SCORE_MODE_LABELS.get(score_mode, "攻撃")


def get_total_score_rank(score_total: float):
    if score_total >= 220:
        return "SS"
    if score_total >= 200:
        return "S"
    if score_total >= 180:
        return "A"
    return "B"


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


def get_artifacts_data(char, loc_data, score_mode: str):
    artifacts = {}
    scores = {"State": get_score_label_for_display(score_mode)}
    atftype_for_counter = []

    for equip in char.get("equipList", []):
        if "reliquary" not in equip:
            continue

        flat = equip.get("flat", {})
        reliquary = equip.get("reliquary", {})

        slot_key = EQUIP_SLOT_MAP.get(flat.get("equipType"))
        if not slot_key:
            continue

        set_name = get_localized_text(loc_data, flat.get("setNameTextMapHash"), "ja") or "不明"
        atftype_for_counter.append(set_name)

        level = int(reliquary.get("level", 1)) - 1
        if level < 0:
            level = 0

        rank_level = int(flat.get("rankLevel", 5))

        main = flat.get("reliquaryMainstat", {})
        main_option = PROP_ID_TO_JP.get(main.get("mainPropId"), main.get("mainPropId"))
        main_value = main.get("statValue", 0)
        if main.get("mainPropId") in PERCENT_PROP_IDS:
            main_value = round(float(main_value), 1)
        else:
            main_value = int(float(main_value)) if float(main_value).is_integer() else round(float(main_value), 1)

        subs = []
        for sub in flat.get("reliquarySubstats", []):
            option = PROP_ID_TO_JP.get(sub.get("appendPropId"), sub.get("appendPropId"))
            value = sub.get("statValue", 0)
            if sub.get("appendPropId") in PERCENT_PROP_IDS:
                value = round(float(value), 1)
            else:
                value = int(float(value)) if float(value).is_integer() else round(float(value), 1)

            subs.append({
                "option": option,
                "value": value
            })

        part_score = calculate_artifact_score(subs, score_mode)
        scores[slot_key] = part_score

        artifacts[slot_key] = {
            "type": set_name,
            "Level": level,
            "rarelity": rank_level,
            "main": {
                "option": main_option,
                "value": main_value
            },
            "sub": subs
        }

    total = 0.0
    for part in ("flower", "wing", "clock", "cup", "crown"):
        total += float(scores.get(part, 0.0))
    scores["total"] = round(total, 1)

    return artifacts, scores


def build_generation_data(raw_data, char, characters_data, loc_data, score_mode: str):
    player_info = raw_data.get("playerInfo", {})
    character_name = get_character_name(char, characters_data, loc_data)

    costume_id = char.get("costumeId")
    if costume_id is not None:
        costume_id = str(costume_id)

    fight_prop_map = char.get("fightPropMap", {})
    prop_map = char.get("propMap", {})

    element_name = get_element_name_from_char(char, characters_data)
    element_short = element_name.replace("元素ダメージ", "")

    hp = int(get_status_value(fight_prop_map, "HP"))
    atk = int(get_status_value(fight_prop_map, "攻撃力"))
    defense = int(get_status_value(fight_prop_map, "防御力"))
    em = int(get_status_value(fight_prop_map, "元素熟知"))
    crit_rate = round(get_status_value(fight_prop_map, "会心率") * 100, 1)
    crit_dmg = round(get_status_value(fight_prop_map, "会心ダメージ") * 100, 1)
    recharge = round(get_status_value(fight_prop_map, "元素チャージ効率") * 100, 1)
    element_bonus_value = round(get_status_value(fight_prop_map, element_name) * 100, 1)

    base_hp = int(get_base_status_value(fight_prop_map, "HP"))
    base_atk = int(get_base_status_value(fight_prop_map, "攻撃力"))
    base_def = int(get_base_status_value(fight_prop_map, "防御力"))

    weapon_info = get_weapon_info(char, loc_data)
    talent_info = get_talent_levels(char, characters_data)
    constellation_count = len(char.get("talentIdList", []))
    friendship = int(player_info.get("friendshipLevel", char.get("fetterInfo", {}).get("expLevel", 10)))
    level = int(prop_map.get("4001", {}).get("val", 1))

    artifacts_data, score_data = get_artifacts_data(char, loc_data, score_mode)

    return {
        "元素": element_short,
        "Character": {
            "Name": character_name,
            "Const": constellation_count,
            "Level": level,
            "Love": friendship,
            "Status": {
             "HP": hp,
                "攻撃力": atk,
                "防御力": defense,
                "元素熟知": em,
                "会心率": crit_rate,
                "会心ダメージ": crit_dmg,
                "元素チャージ効率": recharge,
                element_name: element_bonus_value,
            },
            "Base": {
                "HP": base_hp,
                "攻撃力": base_atk,
                "防御力": base_def,
            },
            "Talent": talent_info,
            "Costume": costume_id
        },
        "Weapon": weapon_info,
        "Score": score_data,
        "Artifacts": artifacts_data
    }


# ====描画====

def generation(data):
    element = data.get('元素')

    CharacterData: dict = data.get('Character')
    CharacterName: str = CharacterData.get('Name')
    CharacterConstellations: int = CharacterData.get('Const')
    CharacterLevel: int = CharacterData.get('Level')
    FriendShip: int = CharacterData.get('Love')
    CharacterStatus: dict = CharacterData.get('Status')
    CharacterBase: dict = CharacterData.get('Base')
    CharacterTalent: dict = CharacterData.get('Talent')

    Weapon: dict = data.get('Weapon')
    WeaponName: str = Weapon.get('name')
    WeaponLevel: int = Weapon.get('Level')
    WeaponRank: int = Weapon.get('totu')
    WeaponRarelity: int = Weapon.get('rarelity')
    WeaponBaseATK: int = Weapon.get('BaseATK')
    WeaponSubOP: dict = Weapon.get('Sub') or {}
    WeaponSubOPKey: str = WeaponSubOP.get('name')
    WeaponSubOPValue = WeaponSubOP.get('value')

    ScoreData: dict = data.get('Score')
    ScoreCVBasis: str = ScoreData.get('State')
    ScoreTotal: float = ScoreData.get('total')

    ArtifactsData: dict = data.get('Artifacts')

    config_font = lambda size: open_font_url(github_url("Assets", "ja-jp.ttf"), size)

    Base = open_image_url(github_url("Base", f"{element}.png"), "RGBA")

    CharacterCostume = CharacterData.get('Costume')

    # 天賦・命ノ星座用の参照先
    if CharacterName in ['蛍', '空', '旅人']:
        traveler_folder = f'蛍({element})' if CharacterName in ['蛍', '旅人'] else f'空({element})'
        character_asset_folder = traveler_folder
    else:
        character_asset_folder = CharacterName

    # 立ち絵
    if CharacterName in ['蛍', '空', '旅人']:
        if CharacterCostume:
            CharacterImage = open_image_url(
                github_url("character", "旅人", f"{CharacterCostume}.png"),
                "RGBA"
            )
        else:
            CharacterImage = open_image_url(
                github_url("character", character_asset_folder, "avatar.png"),
                "RGBA"
            )
    else:
        if CharacterCostume:
            CharacterImage = open_image_url(
                github_url("character", CharacterName, f"{CharacterCostume}.png"),
                "RGBA"
            )
        else:
            CharacterImage = open_image_url(
                github_url("character", CharacterName, "avatar.png"),
                "RGBA"
            )
                
    Shadow = open_image_url(
        github_url("Assets", "Shadow.png"),
        "RGBA"
    ).resize(Base.size)

    CharacterImage = CharacterImage.crop((289, 0, 1728, 1024))
    CharacterImage = CharacterImage.resize((int(CharacterImage.width * 0.75), int(CharacterImage.height * 0.75)))

    CharacterAvatarMask = CharacterImage.copy()

    if CharacterName == 'アルハイゼン':
        CharacterAvatarMask2 = open_image_url(
            github_url("Assets", "Alhaitham.png"),
            "RGBA"
        ).convert("L").resize(CharacterImage.size)
    else:
        CharacterAvatarMask2 = open_image_url(
            github_url("Assets", "CharacterMask.png"),
            "RGBA"
        ).convert("L").resize(CharacterImage.size)

    CharacterImage.putalpha(CharacterAvatarMask2)

    CharacterPaste = Image.new("RGBA", Base.size, (255, 255, 255, 0))
    CharacterPaste.paste(CharacterImage, (-160, -45), mask=CharacterAvatarMask)
    Base = Image.alpha_composite(Base, CharacterPaste)
    Base = Image.alpha_composite(Base, Shadow)

    WeaponImage = open_image_url(
        github_url("weapon", f"{WeaponName}.png"),
        "RGBA"
    ).resize((128, 128))
    WeaponPaste = Image.new("RGBA", Base.size, (255, 255, 255, 0))
    WeaponMask = WeaponImage.copy()
    WeaponPaste.paste(WeaponImage, (1430, 50), mask=WeaponMask)
    Base = Image.alpha_composite(Base, WeaponPaste)

    WeaponRImage = open_image_url(
        github_url("Assets", "Rarelity", f"{WeaponRarelity}.png"),
        "RGBA"
    )
    WeaponRImage = WeaponRImage.resize((int(WeaponRImage.width * 0.97), int(WeaponRImage.height * 0.97)))
    WeaponRPaste = Image.new("RGBA", Base.size, (255, 255, 255, 0))
    WeaponRMask = WeaponRImage.copy()
    WeaponRPaste.paste(WeaponRImage, (1422, 173), mask=WeaponRMask)
    Base = Image.alpha_composite(Base, WeaponRPaste)

    TalentBase = open_image_url(
        github_url("Assets", "TalentBack.png"),
        "RGBA"
    )
    TalentBasePaste = Image.new("RGBA", Base.size, (255, 255, 255, 0))
    TalentBase = TalentBase.resize((int(TalentBase.width / 1.5), int(TalentBase.height / 1.5)))

    for i, t in enumerate(['通常', 'スキル', "爆発"]):
        TalentPaste = Image.new("RGBA", TalentBase.size, (255, 255, 255, 0))
        Talent = open_image_url(
                github_url("character", character_asset_folder, f"{t}.png"),
                "RGBA"
            ).resize((50, 50)).convert('RGBA')
        TalentMask = Talent.copy()
        TalentPaste.paste(Talent, (TalentPaste.width // 2 - 25, TalentPaste.height // 2 - 25), mask=TalentMask)

        TalentObject = Image.alpha_composite(TalentBase, TalentPaste)
        TalentBasePaste.paste(TalentObject, (15, 330 + i * 105))

    Base = Image.alpha_composite(Base, TalentBasePaste)

    CBase = open_image_url(
            github_url("命の星座", f"{element}.png"),
            "RGBA"
        ).resize((90, 90))

    Clock = open_image_url(
            github_url("命の星座", f"{element}LOCK.png"),
            "RGBA"
        ).resize((90, 90))
    ClockMask = Clock.copy()

    CPaste = Image.new("RGBA", Base.size, (255, 255, 255, 0))
    for c in range(1, 7):
        if c > CharacterConstellations:
            CPaste.paste(Clock, (666, -10 + c * 93), mask=ClockMask)
        else:
            CharaC = open_image_url(
                    github_url("character", character_asset_folder, f"{c}.png"),
                    "RGBA"
                ).resize((45, 45))
            CharaCPaste = Image.new("RGBA", CBase.size, (255, 255, 255, 0))
            CharaCMask = CharaC.copy()
            CharaCPaste.paste(CharaC, (int(CharaCPaste.width / 2) - 25, int(CharaCPaste.height / 2) - 23), mask=CharaCMask)

            Cobject = Image.alpha_composite(CBase, CharaCPaste)
            CPaste.paste(Cobject, (666, -10 + c * 93))

    Base = Image.alpha_composite(Base, CPaste)
    D = ImageDraw.Draw(Base)

    D.text((30, 20), CharacterName, font=config_font(48))
    levellength = D.textlength("Lv." + str(CharacterLevel), font=config_font(25))
    friendshiplength = D.textlength(str(FriendShip), font=config_font(25))
    D.text((35, 75), "Lv." + str(CharacterLevel), font=config_font(25))
    D.rounded_rectangle((35 + levellength + 5, 74, 77 + levellength + friendshiplength, 102), radius=2, fill="black")

    FriendShipIcon = open_image_url(
        github_url("Assets", "Love.png"),
        "RGBA"
    )
    FriendShipIcon = FriendShipIcon.resize((int(FriendShipIcon.width * (24 / FriendShipIcon.height)), 24))
    Fmask = FriendShipIcon.copy()
    Base.paste(FriendShipIcon, (42 + int(levellength), 76), mask=Fmask)
    D.text((73 + levellength, 74), str(FriendShip), font=config_font(25))

    D.text((42, 397), f'Lv.{CharacterTalent["通常"]}', font=config_font(17), fill='aqua' if CharacterTalent["通常"] >= 10 else None)
    D.text((42, 502), f'Lv.{CharacterTalent["スキル"]}', font=config_font(17), fill='aqua' if CharacterTalent["スキル"] >= 10 else None)
    D.text((42, 607), f'Lv.{CharacterTalent["爆発"]}', font=config_font(17), fill='aqua' if CharacterTalent["爆発"] >= 10 else None)

    def genbasetext(state):
        sumv = CharacterStatus[state]
        plusv = sumv - CharacterBase[state]
        basev = CharacterBase[state]
        return (
            f"+{format(plusv, ',')}",
            f"{format(basev, ',')}",
            D.textlength(f"+{format(plusv, ',')}", font=config_font(12)),
            D.textlength(f"{format(basev, ',')}", font=config_font(12))
        )

    disper = [
        '会心率', '会心ダメージ', '攻撃パーセンテージ', '防御パーセンテージ', 'HPパーセンテージ',
        '水元素ダメージ', '物理ダメージ', '風元素ダメージ', '岩元素ダメージ', '炎元素ダメージ',
        '与える治癒効果', '与える治療効果', '雷元素ダメージ', '氷元素ダメージ', '草元素ダメージ',
        '与える治癒効果', '元素チャージ効率'
    ]
    StateOP = ('HP', '攻撃力', "防御力", "元素熟知", "会心率", "会心ダメージ", "元素チャージ効率")

    for k, v in CharacterStatus.items():
        if k in ['氷元素ダメージ', '水元素ダメージ', '岩元素ダメージ', '草元素ダメージ', '風元素ダメージ', '炎元素ダメージ', '物理ダメージ', '与える治癒効果', '雷元素ダメージ'] and v == 0:
            k = f'{element}元素ダメージ'
        try:
            i = StateOP.index(k)
        except Exception:
            i = 7
            D.text((844, 67 + i * 70), k, font=config_font(26))
            opicon = open_image_url(
                github_url("emotes", f"{k}.png"),
                "RGBA"
            ).resize((40, 40))
            oppaste = Image.new('RGBA', Base.size, (255, 255, 255, 0))
            oppaste.paste(opicon, (789, 65 + i * 70))
            Base = Image.alpha_composite(Base, oppaste)
            D = ImageDraw.Draw(Base)

        if k not in disper:
            statelen = D.textlength(format(v, ","), config_font(26))
            D.text((1360 - statelen, 67 + i * 70), format(v, ","), font=config_font(26))
        else:
            statelen = D.textlength(f'{float(v)}%', config_font(26))
            D.text((1360 - statelen, 67 + i * 70), f'{float(v)}%', font=config_font(26))

        if k in ['HP', '防御力', '攻撃力']:
            HPpls, HPbase, HPsize, HPbsize = genbasetext(k)
            D.text((1360 - HPsize, 97 + i * 70), HPpls, fill=(0, 255, 0, 180), font=config_font(12))
            D.text((1360 - HPsize - HPbsize - 1, 97 + i * 70), HPbase, font=config_font(12), fill=(255, 255, 255, 180))

    D.text((1582, 47), WeaponName, font=config_font(26))
    wlebellen = D.textlength(f'Lv.{WeaponLevel}', font=config_font(24))
    D.rounded_rectangle((1582, 80, 1582 + wlebellen + 4, 108), radius=1, fill='black')
    D.text((1584, 82), f'Lv.{WeaponLevel}', font=config_font(24))

    BaseAtk = open_image_url(
        github_url("emotes", "基礎攻撃力.png"),
        "RGBA"
    ).resize((23, 23))
    BaseAtkmask = BaseAtk.copy()
    Base.paste(BaseAtk, (1600, 120), mask=BaseAtkmask)
    D.text((1623, 120), f'基礎攻撃力  {WeaponBaseATK}', font=config_font(23))

    optionmap = {
        "攻撃パーセンテージ": "攻撃%",
        "防御パーセンテージ": "防御%",
        "元素チャージ効率": "元チャ効率",
        "HPパーセンテージ": "HP%",
    }
    if WeaponSubOPKey is not None:
        BaseAtk = open_image_url(
            github_url("emotes", f"{WeaponSubOPKey}.png"),
            "RGBA"
        ).resize((23, 23))
        BaseAtkmask = BaseAtk.copy()
        Base.paste(BaseAtk, (1600, 155), mask=BaseAtkmask)

        value_text = str(WeaponSubOPValue) + "%" if WeaponSubOPKey in disper else format(WeaponSubOPValue, ",")
        D.text((1623, 155), f'{optionmap.get(WeaponSubOPKey) or WeaponSubOPKey}  {value_text}', font=config_font(23))

    D.rounded_rectangle((1430, 45, 1470, 70), radius=1, fill='black')
    D.text((1433, 46), f'R{WeaponRank}', font=config_font(24))

    ScoreLen = D.textlength(f'{ScoreTotal}', config_font(75))
    D.text((1652 - ScoreLen // 2, 420), str(ScoreTotal), font=config_font(75))
    blen = D.textlength(f'{ScoreCVBasis}換算', config_font(24))
    score_basis_x = 1867 - blen
    score_basis_y = 585
    D.text((score_basis_x, score_basis_y), f'{ScoreCVBasis}換算', font=config_font(24))

    if ScoreTotal >= 220:
        ScoreEv = open_image_url(
            github_url("artifactGrades", "SS.png"),
            "RGBA"
        )
    elif ScoreTotal >= 200:
        ScoreEv = open_image_url(
            github_url("artifactGrades", "S.png"),
            "RGBA"
        )
    elif ScoreTotal >= 180:
        ScoreEv = open_image_url(
            github_url("artifactGrades", "A.png"),
            "RGBA"
        )
    else:
        ScoreEv = open_image_url(
            github_url("artifactGrades", "B.png"),
            "RGBA"
        )

    ScoreEv = ScoreEv.resize((ScoreEv.width // 8, ScoreEv.height // 8))
    EvMask = ScoreEv.copy()
    Base.paste(ScoreEv, (1806, 345), mask=EvMask)

    # ===== dokokai ロゴ + テキスト =====
    logo_text = "ﾄﾞｺｶｲArtifacter"
    logo_font = config_font(24)

    logo_y = score_basis_y - 1

    icon_size = 30
    icon_x = 1440
    icon_y = logo_y - 2

    try:
        dokokai_icon = open_image_url(
            github_url("dokokai_icon.png"),
            "RGBA"
        )
        dokokai_icon = ImageOps.fit(
            dokokai_icon,
            (icon_size, icon_size),
            method=Image.Resampling.LANCZOS
        )
        Base.paste(dokokai_icon, (icon_x, icon_y), mask=dokokai_icon)
    except requests.RequestException:
        pass

    text_x = icon_x + icon_size + 10
    D.text((text_x, logo_y), logo_text, font=logo_font, fill="white")

    atftype = list()
    for i, parts in enumerate(['flower', "wing", "clock", "cup", "crown"]):
        details = ArtifactsData.get(parts)
        if not details:
            continue

        atftype.append(details['type'])
        PreviewPaste = Image.new('RGBA', Base.size, (255, 255, 255, 0))
        Preview = open_image_url(
            github_url("Artifact", details["type"], f"{parts}.png"),
            "RGBA"
        ).resize((256, 256))
        enhancer = ImageEnhance.Brightness(Preview)
        Preview = enhancer.enhance(0.6)
        Preview = Preview.resize((int(Preview.width * 1.3), int(Preview.height * 1.3)))
        Pmask1 = Preview.copy()

        Pmask = open_image_url(
            github_url("Assets", "ArtifactMask.png"),
            "RGBA"
        ).convert("L").resize(Preview.size)
        Preview.putalpha(Pmask)

        if parts in ['flower', 'crown']:
            PreviewPaste.paste(Preview, (-37 + 373 * i, 570), mask=Pmask1)
        elif parts in ['wing', 'cup']:
            PreviewPaste.paste(Preview, (-36 + 373 * i, 570), mask=Pmask1)
        else:
            PreviewPaste.paste(Preview, (-35 + 373 * i, 570), mask=Pmask1)

        Base = Image.alpha_composite(Base, PreviewPaste)
        D = ImageDraw.Draw(Base)

        mainop = details['main']['option']
        mainoplen = D.textlength(optionmap.get(mainop) or mainop, font=config_font(29))
        D.text((375 + i * 373 - int(mainoplen), 655), optionmap.get(mainop) or mainop, font=config_font(29))

        MainIcon = open_image_url(
            github_url("emotes", f"{mainop}.png"),
            "RGBA"
        ).resize((35, 35))
        MainMask = MainIcon.copy()
        Base.paste(MainIcon, (340 + i * 373 - int(mainoplen), 655), mask=MainMask)

        mainv = details['main']['value']
        if mainop in disper:
            mainvsize = D.textlength(f'{float(mainv)}%', config_font(49))
            D.text((375 + i * 373 - mainvsize, 690), f'{float(mainv)}%', font=config_font(49))
        else:
            mainvsize = D.textlength(format(mainv, ","), config_font(49))
            D.text((375 + i * 373 - mainvsize, 690), format(mainv, ","), font=config_font(49))

        levlen = D.textlength(f'+{details["Level"]}', config_font(21))
        D.rounded_rectangle((373 + i * 373 - int(levlen), 748, 375 + i * 373, 771), fill='black', radius=2)
        D.text((374 + i * 373 - levlen, 749), f'+{details["Level"]}', font=config_font(21))

        psb = None
        if details['Level'] == 20 and details['rarelity'] == 5:
            c_data = {}
            for a in details["sub"]:
                if a['option'] in disper:
                    c_data[a['option']] = str(float(a["value"]))
                else:
                    c_data[a['option']] = str(a["value"])
            psb = culculate_op(c_data)

        if len(details['sub']) == 0:
            continue

        for a, sub in enumerate(details['sub']):
            SubOP = sub['option']
            SubVal = sub['value']
            if SubOP in ['HP', '攻撃力', '防御力']:
                D.text((79 + 373 * i, 811 + 50 * a), optionmap.get(SubOP) or SubOP, font=config_font(25), fill=(255, 255, 255, 190))
            else:
                D.text((79 + 373 * i, 811 + 50 * a), optionmap.get(SubOP) or SubOP, font=config_font(25))

            SubIcon = open_image_url(
                github_url("emotes", f"{SubOP}.png"),
                "RGBA"
            ).resize((30, 30))
            SubMask = SubIcon.copy()
            Base.paste(SubIcon, (44 + 373 * i, 811 + 50 * a), mask=SubMask)

            if SubOP in disper:
                SubSize = D.textlength(f'{float(SubVal)}%', config_font(25))
                D.text((375 + i * 373 - SubSize, 811 + 50 * a), f'{float(SubVal)}%', font=config_font(25))
            else:
                SubSize = D.textlength(format(SubVal, ","), config_font(25))
                if SubOP in ['防御力', '攻撃力', 'HP']:
                    D.text((375 + i * 373 - SubSize, 811 + 50 * a), format(SubVal, ","), font=config_font(25), fill=(255, 255, 255, 190))
                else:
                    D.text((375 + i * 373 - SubSize, 811 + 50 * a), format(SubVal, ","), font=config_font(25), fill=(255, 255, 255))

            if details['Level'] == 20 and details['rarelity'] == 5 and psb is not None and psb[a] is not None:
                nobi = D.textlength("+".join(map(str, psb[a])), font=config_font(11))
                D.text((375 + i * 373 - nobi, 840 + 50 * a), "+".join(map(str, psb[a])), fill=(255, 255, 255, 160), font=config_font(11))

        Score = float(ScoreData[parts])
        ATFScorelen = D.textlength(str(Score), config_font(36))
        D.text((380 + i * 373 - ATFScorelen, 1016), str(Score), font=config_font(36))
        D.text((295 + i * 373 - ATFScorelen, 1025), 'Score', font=config_font(27), fill=(160, 160, 160))

        PointRefer = {
            "total": {"SS": 220, "S": 200, "A": 180},
            "flower": {"SS": 50, "S": 45, "A": 40},
            "wing": {"SS": 50, "S": 45, "A": 40},
            "clock": {"SS": 45, "S": 40, "A": 35},
            "cup": {"SS": 45, "S": 40, "A": 37},
            "crown": {"SS": 40, "S": 35, "A": 30}
        }

        if Score >= PointRefer[parts]['SS']:
            ScoreImage = open_image_url(
                github_url("artifactGrades", "SS.png"),
                "RGBA"
            )
        elif Score >= PointRefer[parts]['S']:
            ScoreImage = open_image_url(
                github_url("artifactGrades", "S.png"),
                "RGBA"
            )
        elif Score >= PointRefer[parts]['A']:
            ScoreImage = open_image_url(
                github_url("artifactGrades", "A.png"),
                "RGBA"
            )
        else:
            ScoreImage = open_image_url(
                github_url("artifactGrades", "B.png"),
                "RGBA"
            )

        ScoreImage = ScoreImage.resize((ScoreImage.width // 11, ScoreImage.height // 11))
        SCMask = ScoreImage.copy()
        Base.paste(ScoreImage, (85 + 373 * i, 1013), mask=SCMask)

    SetBounus = Counter([x for x in atftype if atftype.count(x) >= 2])
    for i, (n, q) in enumerate(SetBounus.items()):
        if len(SetBounus) == 2:
            D.text((1536, 243 + i * 35), n, fill=(0, 255, 0), font=config_font(23))
            D.rounded_rectangle((1818, 243 + i * 35, 1862, 266 + i * 35), 1, 'black')
            D.text((1835, 243 + i * 35), str(q), font=config_font(19))
        if len(SetBounus) == 1:
            D.text((1536, 263), n, fill=(0, 255, 0), font=config_font(23))
            D.rounded_rectangle((1818, 263, 1862, 288), 1, 'black')
            D.text((1831, 265), str(q), font=config_font(19))

    result = pil_to_bytes(Base, "PNG")
    Base.close()
    return result


# ====Embed====

def build_profile_embed(data, characters, characters_data, loc_data, uid):
    player_info = data.get("playerInfo", {})

    nickname = player_info.get("nickname", "不明")
    signature = player_info.get("signature", "なし")
    adventure_rank = player_info.get("level", "不明")
    world_level = player_info.get("worldLevel", "不明")
    achievement_count = player_info.get("finishAchievementNum", "不明")
    tower_floor = player_info.get("towerFloorIndex", 0)
    tower_room = player_info.get("towerLevelIndex", 0)
    name_card_id = player_info.get("nameCardId", "不明")

    public_char_count = len(characters)

    chara_lines = []
    for char in characters[:9]:
        name = get_character_name(char, characters_data, loc_data)
        level = char.get("propMap", {}).get("4001", {}).get("val", "不明")
        chara_lines.append(f"・{name} Lv.{level}")

    if not chara_lines:
        chara_lines.append("公開キャラクターなし")

    abyss_text = "未記録"
    if tower_floor and tower_room:
        abyss_text = f"{tower_floor}-{tower_room}"

    embed = discord.Embed(
        title=f"{nickname} のプロフィール",
        description=f"UID: {uid}"
    )

    embed.add_field(
        name="基本情報",
        value=(
            f"冒険ランク: {adventure_rank}\n"
            f"世界ランク: {world_level}\n"
            f"実績数: {achievement_count}\n"
            f"深境螺旋: {abyss_text}\n"
            f"公開キャラ数: {public_char_count}"
        ),
        inline=False
    )

    embed.add_field(
        name="コメント",
        value=signature if signature else "なし",
        inline=False
    )

    embed.add_field(
        name="公開キャラクター",
        value="\n".join(chara_lines),
        inline=False
    )

    profile_icon_url = get_profile_icon_url(player_info, characters_data)
    if profile_icon_url:
        embed.set_thumbnail(url=profile_icon_url)

    embed.set_footer(text="キャラクター選択後に画像生成ボタンを押すとビルドカードを作成します")
    return embed


def build_selected_character_embed(data, char, characters_data, loc_data, score_mode):
    player_info = data.get("playerInfo", {})
    nickname = player_info.get("nickname", "不明")
    ar = player_info.get("level", "不明")
    wl = player_info.get("worldLevel", "不明")

    name = get_character_name(char, characters_data, loc_data)
    level = char.get("propMap", {}).get("4001", {}).get("val", "不明")
    talents = get_talent_levels(char, characters_data)
    constellations = len(char.get("talentIdList", []))
    score_label = SCORE_MODE_LABELS.get(score_mode, "攻撃")

    embed = discord.Embed(
        title=f"{name} を選択中",
        description=(
            f"{nickname} / AR{ar} / WL{wl}\n"
            f"Lv.{level} / {constellations}凸\n"
            f"天賦: {talents['通常']}/{talents['スキル']}/{talents['爆発']}\n"
            f"スコア方式: {score_label}"
        )
    )
    embed.set_footer(text="画像生成ボタンを押すとビルドカードを表示します")
    return embed


# ====UI====

class CharacterSelect(discord.ui.Select):
    def __init__(self, view, options):
        super().__init__(
            placeholder="キャラクターを選択してください",
            min_values=1,
            max_values=1,
            options=options,
            row=0
        )
        self.parent_view = view

    async def callback(self, interaction: discord.Interaction):
        selected_value = self.values[0]

        if selected_value == "profile":
            self.parent_view.current_page = "profile"
            self.parent_view.current_character_index = None

            embed = build_profile_embed(
                data=self.parent_view.data,
                characters=self.parent_view.characters,
                characters_data=self.parent_view.characters_data,
                loc_data=self.parent_view.loc_data,
                uid=self.parent_view.uid
            )

            await interaction.response.edit_message(
                content="プロフィールを表示中です。",
                embed=embed,
                view=self.parent_view
            )
            return

        selected_index = int(selected_value)
        self.parent_view.current_page = "character"
        self.parent_view.current_character_index = selected_index

        selected_char = self.parent_view.characters[selected_index]
        embed = build_selected_character_embed(
            data=self.parent_view.data,
            char=selected_char,
            characters_data=self.parent_view.characters_data,
            loc_data=self.parent_view.loc_data,
            score_mode=self.parent_view.score_mode
        )

        await interaction.response.edit_message(
            content="キャラクターを選択しました。画像生成ボタンを押してください。",
            embed=embed,
            view=self.parent_view
        )


class ScoreModeButton(discord.ui.Button):
    def __init__(self, view, mode, label, row):
        super().__init__(label=label, style=discord.ButtonStyle.secondary, row=row)
        self.parent_view = view
        self.mode = mode

    async def callback(self, interaction: discord.Interaction):
        self.parent_view.score_mode = self.mode
        self.parent_view.refresh_button_styles()

        if self.parent_view.current_page == "character" and self.parent_view.current_character_index is not None:
            selected_char = self.parent_view.characters[self.parent_view.current_character_index]
            embed = build_selected_character_embed(
                data=self.parent_view.data,
                char=selected_char,
                characters_data=self.parent_view.characters_data,
                loc_data=self.parent_view.loc_data,
                score_mode=self.parent_view.score_mode
            )
            await interaction.response.edit_message(
                content="スコア方式を変更しました。画像生成ボタンを押してください。",
                embed=embed,
                view=self.parent_view
            )
        else:
            embed = build_profile_embed(
                data=self.parent_view.data,
                characters=self.parent_view.characters,
                characters_data=self.parent_view.characters_data,
                loc_data=self.parent_view.loc_data,
                uid=self.parent_view.uid
            )
            await interaction.response.edit_message(
                content="プロフィールを表示中です。",
                embed=embed,
                view=self.parent_view
            )


class GenerateImageButton(discord.ui.Button):
    def __init__(self, view):
        super().__init__(label="画像生成", style=discord.ButtonStyle.success, row=3)
        self.parent_view = view

    async def callback(self, interaction: discord.Interaction):
        if self.parent_view.current_page != "character" or self.parent_view.current_character_index is None:
            await interaction.response.send_message(
                "先にキャラクターを選択してください。",
                ephemeral=True
            )
            return

        await interaction.response.defer()

        selected_char = self.parent_view.characters[self.parent_view.current_character_index]
        generation_data = build_generation_data(
            raw_data=self.parent_view.data,
            char=selected_char,
            characters_data=self.parent_view.characters_data,
            loc_data=self.parent_view.loc_data,
            score_mode=self.parent_view.score_mode
        )

        try:
            image_buffer = generation(generation_data)
            file = discord.File(image_buffer, filename="buildcard.png")

            await interaction.edit_original_response(
                content=f"ビルドカードを表示中です。スコア方式: {SCORE_MODE_LABELS[self.parent_view.score_mode]}",
                embed=None,
                attachments=[],
                files=[file],
                view=self.parent_view
            )

        except requests.HTTPError as e:
            await interaction.edit_original_response(
                content=f"必要な画像またはデータがGitHub上に見つかりませんでした。\n{type(e).__name__}: {e}",
                embed=None,
                attachments=[],
                view=self.parent_view
            )
            return

        except FileNotFoundError as e:
            missing_path = str(e).split(":")[-1].strip().strip("'")
            await interaction.edit_original_response(
                content=f"必要な画像が見つかりませんでした。\n不足ファイル: {missing_path}",
                embed=None,
                attachments=[],
                view=self.parent_view
            )
            return

        except Exception as e:
            await interaction.edit_original_response(
                content=f"画像生成中にエラーが発生しました。\n{type(e).__name__}: {e}",
                embed=None,
                attachments=[],
                view=self.parent_view
            )
            return


class CharacterSelectView(discord.ui.View):
    def __init__(self, author_id, uid, data, characters, characters_data, loc_data):
        super().__init__(timeout=600)
        self.author_id = author_id
        self.uid = uid
        self.data = data
        self.characters = characters
        self.characters_data = characters_data
        self.loc_data = loc_data

        self.current_page = "profile"
        self.current_character_index = None
        self.score_mode = "atk"

        options = [
            discord.SelectOption(
                label="プロフィール",
                description="UIDプロフィール画面に戻ります",
                value="profile"
            )
        ]

        for index, char in enumerate(characters):
            name = get_character_name(char, characters_data, loc_data)
            level = char.get("propMap", {}).get("4001", {}).get("val", "不明")
            options.append(
                discord.SelectOption(
                    label=name[:100],
                    description=f"Lv.{level}",
                    value=str(index)
                )
            )

        self.add_item(CharacterSelect(self, options))

        self.score_buttons = []
        button_defs = [
            ("atk", "攻撃", 1),
            ("def", "防御", 1),
            ("def08", "防御(×0.8)", 1),
            ("hp", "HP", 2),
            ("er", "元素チャージ", 2),
            ("em", "元素熟知", 2),
        ]

        for mode, label, row in button_defs:
            button = ScoreModeButton(self, mode, label, row)
            self.score_buttons.append(button)
            self.add_item(button)

        self.add_item(GenerateImageButton(self))
        self.refresh_button_styles()

    def refresh_button_styles(self):
        for button in self.score_buttons:
            button.style = discord.ButtonStyle.primary if button.mode == self.score_mode else discord.ButtonStyle.secondary

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "このメニューは入力した本人のみ操作できます。",
                ephemeral=True
            )
            return False
        return True


class UIDModal(discord.ui.Modal):
    def __init__(self, cog):
        super().__init__(title="UIDを入力してください")
        self.cog = cog

        self.uid_input = discord.ui.InputText(
            label="UID",
            placeholder="9桁または10桁のUIDを入力してください",
            required=True,
            min_length=9,
            max_length=10
        )
        self.add_item(self.uid_input)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        uid = self.uid_input.value.strip()
        
        if not uid.isdigit():
            await interaction.followup.send(
                "UIDは数字のみで入力してください。",
                 ephemeral=True
            )
            return

        if len(uid) not in (9, 10):
            await interaction.followup.send(
                "UIDは9桁または10桁で入力してください。",
                ephemeral=True
            )
            return

        try:
            now = time.time()
            cache = self.cog.uid_cache.get(uid)

            if cache and now - cache["time"] < 60:
                data = cache["data"]
            else:
                response = HTTP.get(f"https://enka.network/api/uid/{uid}", timeout=20)

                if response.status_code == 429:
                    await interaction.followup.send(
                        "Enka APIのアクセス制限にかかっています。少し時間を空けてからもう一度試してください。",
                        ephemeral=True
                    )
                    return

                response.raise_for_status()
                data = response.json()
                self.cog.uid_cache[uid] = {"time": now, "data": data}
            # データ存在チェック（UID非公開など対策）
            if not data or "avatarInfoList" not in data:
                await interaction.response.send_message(
                    "キャラクターデータが取得できませんでした（UID非公開の可能性があります）。",
                    ephemeral=True
                )
                return

        except requests.Timeout:
            await interaction.followup.send(
                "Enka APIがタイムアウトしました。しばらく待って再度お試しください。",
                ephemeral=True
            )
            return

        except requests.HTTPError as e:
            await interaction.followup.send(
                f"Enka APIでエラーが発生しました。\nHTTP {response.status_code}",
                ephemeral=True
            )
            return

        except requests.RequestException:
            await interaction.followup.send(
                "Enka APIへの接続に失敗しました。",
                ephemeral=True
            )
            return

        except ValueError:
            await interaction.followup.send(
                "APIレスポンスの解析に失敗しました。",
                ephemeral=True
            )
            return

        if "avatarInfoList" not in data:
            await interaction.followup.send(
                "キャラ取得失敗。UIDが正しいか、公開設定になっているか確認してください。",
                ephemeral=True
            )
            return

        characters = data["avatarInfoList"]
        if not characters:
            await interaction.followup.send(
                "公開キャラクターが見つかりませんでした。",
                ephemeral=True
            )
            return

        view = CharacterSelectView(
            author_id=interaction.user.id,
            uid=uid,
            data=data,
            characters=characters,
            characters_data=self.cog.characters_data,
            loc_data=self.cog.loc_data
        )

        profile_embed = build_profile_embed(
            data=data,
            characters=characters,
            characters_data=self.cog.characters_data,
            loc_data=self.cog.loc_data,
            uid=uid
        )

        await interaction.followup.send(
            content="プロフィールを表示中です。",
            embed=profile_embed,
            view=view,
            ephemeral=True
        )


class UIDInputButton(discord.ui.Button):
    def __init__(self, cog):
        super().__init__(label="ビルドカードを生成", style=discord.ButtonStyle.primary, row=0)
        self.cog = cog

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(UIDModal(self.cog))


class UIDInputView(discord.ui.View):
    def __init__(self, cog):
        super().__init__(timeout=None)
        self.add_item(UIDInputButton(cog))


class GenshinCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.characters_data = load_json(CHARACTERS_JSON_URL)
        self.loc_data = load_json(LOC_JSON_URL)
        self.uid_cache = {}

    @commands.slash_command(name="genshin_build", description="原神プロフィール表示ボタンを送信")
    async def genshin_build(self, ctx):
        view = UIDInputView(self)

        embed = discord.Embed(
        title="原神ビルドカード",
        description="同好会のマーク付きビルドカードを生成できます",
        color=0x00BFFF
    )

        embed.add_field(
            name="手順",
            value=(
                "① ボタンを押してUIDを入力\n"
                "② キャラクター・換算方式を選択\n"
                "③ 「画像生成」を押す"
            ),
            inline=False
        )

        embed.set_footer(text="※ UIDは公開設定のもののみ取得可能です")

        await ctx.respond(
            embed=embed,
            view=view
        )

def setup(bot):
    bot.add_cog(GenshinCog(bot))
