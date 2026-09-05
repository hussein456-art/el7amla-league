"""
update_standings.py — المرحلة 1
=================================
الهدف: يجيب نقط اللاعبين الحقيقية من Fantasy Premier League،
يحسب نتيجة كل ماتش (فوز/تعادل/خسارة)، ويرتب الفرق.

من غير نظام خواص لسه — ده هنضيفه في المرحلة الجاية فوق الأساس ده
بعد ما نتأكد إن الحساب الأساسي صح 100%.

طريقة التشغيل:
    python scripts/update_standings.py
"""

import json
import time
from pathlib import Path

import requests

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────

BASE_DIR = Path(__file__).parent
REPO_ROOT = BASE_DIR.parent

LEAGUE_FILE = REPO_ROOT / "data" / "league.json"
FIXTURES_FILE = REPO_ROOT / "data" / "fixtures.json"
CHIPS_FILE = REPO_ROOT / "data" / "chips.json"
OUTPUT_FILE = REPO_ROOT / "data" / "standings.json"

FPL_BASE = "https://fantasy.premierleague.com/api"
API_DELAY = 0.8  # ثانية بين كل طلب وطلب، عشان منضغطش على سيرفر الفانتازي

_entry_gw_cache: dict[tuple[int, int], int] = {}


# ─────────────────────────────────────────────
# FPL API
# ─────────────────────────────────────────────

def get_current_gw() -> int:
    """بيسأل bootstrap-static: آخر جولة خلصت رسمياً رقمها إيه."""
    res = requests.get(f"{FPL_BASE}/bootstrap-static/", timeout=15)
    res.raise_for_status()
    data = res.json()

    for event in reversed(data["events"]):
        if event["finished"]:
            return event["id"]
    return 1


def get_entry_net_points(entry_id: int, gw: int) -> int:
    """
    بيجيب نقاط لاعب معين (entry_id) في جولة معينة، صافية بعد خصم الانتقالات.
    بيحفظ النتيجة في cache عشان لو نفس اللاعب اتطلب تاني في نفس التشغيلة
    منضربش على الـ API تاني من غير داعي.

    ملحوظة مهمة: لو اللاعب دخل يلعب فانتازي متأخر (بعد ما الجولة دي خلصت
    فعلياً)، الفانتازي بيرجع 404 لأن مفيش بيانات ليه في الجولة دي أصلاً.
    الحالة دي مش خطأ فعلي — بنعتبرها ببساطة 0 نقطة في الجولة دي ونكمل.
    """
    cache_key = (entry_id, gw)
    if cache_key in _entry_gw_cache:
        return _entry_gw_cache[cache_key]

    url = f"{FPL_BASE}/entry/{entry_id}/event/{gw}/picks/"
    res = requests.get(url, timeout=15)

    if res.status_code == 404:
        print(f"   ⚠️  entry {entry_id} مفيهوش بيانات في GW{gw} (لسه ما كانش داخل) — هتتحسب صفر")
        _entry_gw_cache[cache_key] = 0
        time.sleep(API_DELAY)
        return 0

    res.raise_for_status()
    data = res.json()

    history = data["entry_history"]
    net_points = history["points"] - history["event_transfers_cost"]

    _entry_gw_cache[cache_key] = net_points
    time.sleep(API_DELAY)
    return net_points


# ─────────────────────────────────────────────
# LEAGUE LOGIC
# ─────────────────────────────────────────────

def load_json(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def get_team_player_points(team_name: str, league: dict, gw: int) -> dict[str, int]:
    """بيرجع نقاط كل لاعب في الفريق لوحده: { 'اسم اللاعب': نقاطه }"""
    players = league["teams"][team_name]["players"]
    return {p["name"]: get_entry_net_points(p["entry_id"], gw) for p in players}


def apply_double_player_chip(team: str, gw: int, player_points: dict[str, int], chips: dict) -> dict[str, int]:
    """
    خاصية double_player: الفريق بيختار لاعب من لاعبينه يضاعف نقطه (×2)،
    مقابل لاعبه التاني تتصفر نقطه (×0) في نفس الجولة.
    بترجع نسخة معدّلة من نقاط اللاعبين.
    """
    adjusted = dict(player_points)
    for entry in chips.get("double_player", []):
        if entry["team"] == team and entry["gw"] == gw:
            doubled = entry.get("doubledPlayer")
            zeroed = entry.get("zeroedPlayer")
            if doubled in adjusted:
                print(f"   ⚡ {team} استخدم double_player في GW{gw} — {doubled} ×2")
                adjusted[doubled] *= 2
            if zeroed in adjusted:
                print(f"   ⚡ {team} استخدم double_player في GW{gw} — {zeroed} = 0")
                adjusted[zeroed] = 0
    return adjusted


def get_team_gw_points(team_name: str, league: dict, gw: int, chips: dict) -> int:
    """نقاط الفريق في جولة معينة = مجموع نقاط لاعبينه (بعد تطبيق double_player لو موجودة)."""
    player_points = get_team_player_points(team_name, league, gw)
    player_points = apply_double_player_chip(team_name, gw, player_points, chips)
    return sum(player_points.values())


def get_one_v_one_activation(team: str, gw: int, chips: dict) -> dict | None:
    """بيدور هل الفريق ده فعّل تحدي 1v1 في الجولة دي، ولو لقى يرجعه."""
    for entry in chips.get("one_v_one", []):
        if entry["team"] == team and entry["gw"] == gw:
            return entry
    return None


def resolve_one_v_one(home: str, away: str, gw: int, league: dict, chips: dict) -> str | None:
    """
    بيحسم تحدي الـ 1v1 لو فيه فريق فعّله في الماتش ده.
    بيرجع اسم الفريق الفايز بالكامل (3-0)، أو None لو مفيش تحدي/التحدي اتلغى.
    """
    home_duel = get_one_v_one_activation(home, gw, chips)
    away_duel = get_one_v_one_activation(away, gw, chips)

    if home_duel and away_duel:
        print(f"   ⚡ الفريقين فعّلوا 1v1 في نفس الماتش GW{gw} — بيتلغوا والحساب عادي")
        return None

    duel = home_duel or away_duel
    if not duel:
        return None

    team = home if home_duel else away
    opponent = away if home_duel else home

    my_pts = get_team_player_points(team, league, gw).get(duel["myPlayer"])
    opp_pts = get_team_player_points(opponent, league, gw).get(duel["oppPlayer"])

    if my_pts is None or opp_pts is None:
        print(f"   ⚠️  بيانات ناقصة لتحدي 1v1 بين {team} و{opponent} في GW{gw} — بيتجاهل")
        return None

    if my_pts == opp_pts:
        print(f"   ⚡ تحدي 1v1 GW{gw}: {team} ({duel['myPlayer']}: {my_pts}) = {opponent} ({duel['oppPlayer']}: {opp_pts}) — تعادل، الحساب عادي")
        return None

    winner = team if my_pts > opp_pts else opponent
    print(f"   ⚡ تحدي 1v1 GW{gw}: {team} ({duel['myPlayer']}: {my_pts}) ضد {opponent} ({duel['oppPlayer']}: {opp_pts}) — {winner} كسب الماتش كامل")
    return winner


def match_result(home_pts: int, away_pts: int) -> tuple[int, int]:
    """بيرجع (نقاط_الفريق_المضيف, نقاط_الفريق_الضيف) حسب قواعد الدوري: فوز=3, تعادل=1, خسارة=0."""
    if home_pts > away_pts:
        return 3, 0
    if home_pts < away_pts:
        return 0, 3
    return 1, 1


def apply_bonus3_chip(team: str, gw: int, match_pts: int, chips: dict) -> int:
    """
    خاصية bonus3: لو الفريق استخدم الخاصية دي في الجولة دي وفاز فيها،
    ياخد +3 نقاط إضافية فوق نقاط الماتش العادية. غير كده، صفر.
    """
    for entry in chips.get("bonus3", []):
        if entry["team"] == team and entry["gw"] == gw and match_pts == 3:
            return 3
    return 0


def calculate_standings(league: dict, fixtures: dict, chips: dict, current_gw: int) -> dict:
    team_names = list(league["teams"].keys())

    standings = {
        name: {
            "name": name, "played": 0, "won": 0, "draw": 0, "lost": 0,
            "matchPts": 0, "chipBonus": 0, "total": 0,
        }
        for name in team_names
    }

    for gw_block in fixtures["fixtures"]:
        gw = gw_block["gw"]
        if gw > current_gw:
            break  # الجولة دي لسه ما لعبتش

        print(f"🔄 بنحسب GW{gw}...")

        for home, away in gw_block["matches"]:
            home_pts = get_team_gw_points(home, league, gw, chips)
            away_pts = get_team_gw_points(away, league, gw, chips)

            duel_winner = resolve_one_v_one(home, away, gw, league, chips)
            if duel_winner:
                home_match_pts, away_match_pts = (3, 0) if duel_winner == home else (0, 3)
            else:
                home_match_pts, away_match_pts = match_result(home_pts, away_pts)

            for team, match_pts in [(home, home_match_pts), (away, away_match_pts)]:
                s = standings[team]
                s["played"] += 1
                s["matchPts"] += match_pts
                if match_pts == 3:
                    s["won"] += 1
                elif match_pts == 1:
                    s["draw"] += 1
                else:
                    s["lost"] += 1

                bonus = apply_bonus3_chip(team, gw, match_pts, chips)
                if bonus:
                    print(f"   ⚡ {team} استخدم bonus3 في GW{gw} وكسبها — +{bonus} نقاط إضافية")
                s["chipBonus"] += bonus
                s["total"] = s["matchPts"] + s["chipBonus"]

    return standings


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print("🔄 بنجيب آخر جولة خلصت من الفانتازي...")
    current_gw = get_current_gw()
    print(f"✅ آخر جولة خلصت: GW{current_gw}\n")

    league = load_json(LEAGUE_FILE)
    fixtures = load_json(FIXTURES_FILE)
    chips = load_json(CHIPS_FILE) if CHIPS_FILE.exists() else {}

    standings = calculate_standings(league, fixtures, chips, current_gw)

    sorted_teams = sorted(standings.values(), key=lambda t: t["total"], reverse=True)

    output = {
        "current_gw": current_gw,
        "last_updated": time.strftime("%Y-%m-%d %H:%M:%S"),
        "teams": sorted_teams,
    }

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n✅ اتكتب الترتيب في: {OUTPUT_FILE}")
    print("\n📊 الترتيب النهائي:")
    for i, t in enumerate(sorted_teams, 1):
        bonus_note = f" [+{t['chipBonus']} خواص]" if t["chipBonus"] else ""
        print(f"   {i}. {t['name']:<18} — {t['total']} نقطة{bonus_note}  (لعب {t['played']}, فوز {t['won']}, تعادل {t['draw']}, خسارة {t['lost']})")
