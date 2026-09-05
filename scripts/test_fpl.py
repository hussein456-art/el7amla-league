"""
test_fpl.py — سكريبت تجريبي بسيط
الهدف: نتأكد إن الاتصال بموقع Fantasy Premier League شغال،
وإننا قادرين نجيب بيانات حقيقية بيها قبل ما نكتب السكريبت الكبير.

طريقة التشغيل:
    pip install requests
    python scripts/test_fpl.py
"""

import requests

FPL_BASE = "https://fantasy.premierleague.com/api"
MY_ENTRY_ID = 1338459  # entry ID بتاع حسين

def get_current_gw():
    """بيسأل bootstrap-static: 'آخر جولة خلصت رسمياً إيه؟'"""
    url = f"{FPL_BASE}/bootstrap-static/"
    res = requests.get(url, timeout=10)
    res.raise_for_status()
    data = res.json()

    for event in reversed(data["events"]):
        if event["finished"]:
            return event["id"]
    return 1  # لو لسه مفيش جولة خلصت، ابدأ من 1


def get_entry_points(entry_id, gw):
    """بيجيب نقاط اللاعب الصافية في جولة معينة."""
    url = f"{FPL_BASE}/entry/{entry_id}/event/{gw}/picks/"
    res = requests.get(url, timeout=10)
    res.raise_for_status()
    data = res.json()

    history = data["entry_history"]
    raw_points = history["points"]
    transfer_cost = history["event_transfers_cost"]
    net_points = raw_points - transfer_cost

    return {
        "gw": gw,
        "raw_points": raw_points,
        "transfer_cost": transfer_cost,
        "net_points": net_points,
        "num_picks": len(data["picks"]),
    }


if __name__ == "__main__":
    print("🔄 بنسأل الفانتازي عن آخر جولة خلصت...")
    current_gw = get_current_gw()
    print(f"✅ آخر جولة خلصت: GW{current_gw}\n")

    print(f"🔄 بنجيب نقاط entry {MY_ENTRY_ID} في GW{current_gw}...")
    result = get_entry_points(MY_ENTRY_ID, current_gw)

    print("✅ النتيجة:")
    print(f"   الجولة:            GW{result['gw']}")
    print(f"   النقاط الخام:      {result['raw_points']}")
    print(f"   خصم الانتقالات:    {result['transfer_cost']}")
    print(f"   النقاط الصافية:    {result['net_points']}")
    print(f"   عدد اللاعبين:      {result['num_picks']}")
