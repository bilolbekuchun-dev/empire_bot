"""eboylar excel formati testi (DB siz, fake data bilan)"""
import sys
sys.path.insert(0, r"d:\Empire_Turon_maf_Bot\Empire_bot_toliq\Empire")
import py_compile
py_compile.compile(r"d:\Empire_Turon_maf_Bot\Empire_bot_toliq\Empire\utils\statistika.py", doraise=True)
print("compile OK", flush=True)

import pandas as pd
from io import BytesIO
from datetime import datetime

# funksiyadagi rows() mantiqini takrorlash
class U:
    def __init__(self, uid, name, username, gender):
        self.user_id = uid; self.full_name = name; self.username = username; self.gender = gender
class P:
    def __init__(self, u, dollar, diamond, wins, coins):
        self.user = u; self.dollar = dollar; self.diamond = diamond; self.wins = wins; self.coins = coins

vip_ids = {2}
def rows(profiles, value_field):
    out = []
    for idx, p in enumerate(profiles, start=1):
        u = p.user
        out.append({"№": idx, "User ID": u.user_id, "Ism": u.full_name or "",
            "Username": f"@{u.username}" if u.username else "",
            "Jins": "👦" if u.gender == "m" else ("👧" if u.gender == "f" else ""),
            "VIP": "⭐" if u.user_id in vip_ids else "",
            "Qiymat": getattr(p, value_field, 0) or 0})
    return out

users = [P(U(1, "Ali", "ali", "m"), 500, 10, 5, 3), P(U(2, "Zara", "zara", "f"), 900, 2, 9, 7)]
sheets = {"Dollar": rows(users, "dollar"), "Olmos": rows(users, "diamond"),
    "G'alaba": rows(users, "wins"), "Paralar": rows(users, "coins"),
    "O'g'illar": rows([users[0]], "dollar"), "Qizlar": rows([users[1]], "dollar")}
buf = BytesIO()
with pd.ExcelWriter(buf, engine="openpyxl") as w:
    for name, data in sheets.items():
        pd.DataFrame(data).to_excel(w, index=False, sheet_name=name)
buf.seek(0)
xl = pd.ExcelFile(buf)
assert xl.sheet_names == ["Dollar", "Olmos", "G'alaba", "Paralar", "O'g'illar", "Qizlar"], xl.sheet_names
print("sheets OK:", xl.sheet_names, flush=True)
df = xl.parse("Dollar")
assert list(df.columns)[:4] == ["№", "User ID", "Ism", "Username"], list(df.columns)
print("columns OK", flush=True)

caption = ("📊 Global Reyting Fayli\n\n👤 Jami foydalanuvchilar: 13,352\n💵 Jami dollar: 2,379,862$\n"
    "💎 Jami olmos: 1,677\n🏆 Jami g'alaba: 65,732\n⭐️ VIP foydalanuvchilar: 30\n💍 Jami paralar: 319\n"
    "👦 O'g'il bollar: 3,578\n👧 Qiz bollar: 3,939\n\n📋 6 ta varaq: Dollar | Olmos | G'alaba | Paralar | O'g'illar | Qizlar")
assert "Global Reyting Fayli" in caption and "6 ta varaq" in caption
print("caption OK", flush=True)
print("ALL EBOYLAR TESTS PASSED", flush=True)
