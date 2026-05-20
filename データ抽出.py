import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

UID_PATH = None  # 自動検出
CHAR_PATH = BASE_DIR / "characters.json"
LOC_PATH = BASE_DIR / "loc.json"

OUTPUT_PATH = BASE_DIR / "抽出結果.txt"


# ==========================
# 基本処理
# ==========================

def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def find_uid_json():
    for p in BASE_DIR.glob("*.json"):
        if p.name not in ["characters.json", "loc.json"]:
            return p
    raise FileNotFoundError("UID.jsonが見つかりません")


# ==========================
# ProudMap生成（重要）
# ==========================

def generate_proud_map(skill_order):
    result = {}
    for skill_id in skill_order:
        skill_str = str(skill_id)

        # 例: 11301 → 13031
        prefix = skill_str[1:4]
        last = skill_str[-1]     # 1 / 2 / 5

        if last == "1":
            suffix = "31"
        elif last == "2":
            suffix = "32"
        elif last == "5":
            suffix = "39"
        else:
            continue

        proud_id = int(prefix + suffix)
        result[str(skill_id)] = proud_id

    return result


# ==========================
# メイン抽出
# ==========================

def main():
    uid_path = find_uid_json()

    uid_data = load_json(uid_path)
    char_master = load_json(CHAR_PATH)
    loc_data = load_json(LOC_PATH)

    loc_ja = loc_data.get("ja", {})

    existing_ids = set(char_master.keys())

    results = []

    weapon_results = set()
    artifact_results = set()

    existing_loc_ids = set(loc_ja.keys())

    for avatar in uid_data.get("avatarInfoList", []):
        avatar_id = str(avatar.get("avatarId"))

        if avatar_id in existing_ids:
            continue

        skill_map = avatar.get("skillLevelMap", {})
        skill_order = sorted([int(k) for k in skill_map.keys()])

        proud_map = generate_proud_map(skill_order)

        # 名前（loc.jsonにあれば使う）
        name = loc_ja.get(avatar_id, f"キャラ_{avatar_id}")

        # ==========================
        # characters.json形式
        # ==========================

        char_block = f'''"{avatar_id}": {{
  "Element": "元素名",
  "SkillOrder": {skill_order},
  "ProudMap": {json.dumps(proud_map, ensure_ascii=False)},
  "NameTextMapHash": {avatar_id},
  "QualityType": "レアリティ名",
  "WeaponType": "武器名"
}}'''

        # ==========================
        # loc.json形式
        # ==========================

        loc_block = f'''"{avatar_id}": "{name}"'''

        results.append((char_block, loc_block))

        # ==========================
        # 武器・聖遺物抽出
        # ==========================

        for equip in avatar.get("equipList", []):

            flat = equip.get("flat", {})

            # ----------------------
            # 武器
            # ----------------------

            if "weapon" in equip:

                weapon_hash = str(flat.get("nameTextMapHash", ""))

                if weapon_hash and weapon_hash not in existing_loc_ids:

                    weapon_results.add(
                        f'''"{weapon_hash}": "武器名"'''
                    )

            # ----------------------
            # 聖遺物
            # ----------------------

            if "reliquary" in equip:

                artifact_hash = str(flat.get("setNameTextMapHash", ""))

                if artifact_hash and artifact_hash not in existing_loc_ids:

                    artifact_results.add(
                        f'''"{artifact_hash}": "聖遺物名"'''
                    )

    # ==========================
    # 出力
    # ==========================

    lines = []

    lines.append("############################")
    lines.append("# characters.json")
    lines.append("############################\n")

    for c, _ in results:
        lines.append(c + ",\n")

    lines.append("\n############################")
    lines.append("# loc.json (ja)")
    lines.append("############################\n")

    for _, l in results:
        lines.append(l + ",\n")

    lines.append("\n############################")
    lines.append("# 新武器")
    lines.append("############################\n")

    for w in weapon_results:
        lines.append(w + ",\n")

    lines.append("\n############################")
    lines.append("# 新聖遺物")
    lines.append("############################\n")

    for a in artifact_results:
        lines.append(a + ",\n")

    lines.append("\n############################")
    lines.append("# 武器種対応")
    lines.append("############################\n")

    lines.append("""片手剣：WEAPON_SWORD_ONE_HAND
両手剣：WEAPON_CLAYMORE
長柄武器：WEAPON_POLE
弓：WEAPON_BOW
法器：WEAPON_CATALYST
""")

    lines.append("\n############################")
    lines.append("# レアリティ対応")
    lines.append("############################\n")

    lines.append("""星5（オレンジ）：QUALITY_ORANGE
星4（パープル）：QUALITY_PURPLE
""")

    OUTPUT_PATH.write_text("\n".join(lines), encoding="utf-8")

    print("抽出完了")
    print(f"出力: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()