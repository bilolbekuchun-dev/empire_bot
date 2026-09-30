import re

with open("utils/game_logic.py", "r") as f:
    content = f.read()

# Add debug prints to create_game_handler
pattern = r"async def create_game_handler\(message: Message, bot: Bot\):\n(\s+)me = await bot\.get_me\(\)"
replacement = r"""async def create_game_handler(message: Message, bot: Bot):
\1print(f"DEBUG: create_game_handler started for chat {message.chat.id} by user {message.from_user.id}")
\1me = await bot.get_me()"""

content = re.sub(pattern, replacement, content)

pattern2 = r"if not allowed:\n(\s+)return"
replacement2 = r"""if not allowed:
\1print(f"DEBUG: User {message.from_user.id} not allowed to create game (status: {member.status}, game_perm: {game_perm})")
\1return"""
content = re.sub(pattern2, replacement2, content)

pattern3 = r"old_game = await Game\.filter\(chat=chat, is_active=True\)\.first\(\)\n(\s+)if old_game:\n(\s+)if old_game\.phase == \"waiting\":"
replacement3 = r"""old_game = await Game.filter(chat=chat, is_active=True).first()
\1if old_game:
\1\2print(f"DEBUG: Found old active game {old_game.id} with phase {old_game.phase}")
\1\2if old_game.phase == "waiting":"""
content = re.sub(pattern3, replacement3, content)

pattern4 = r"msg = await message\.answer\(\n(\s+)f\"<b>Ro'yxatdan o'tish boshlandi!</b>\""
replacement4 = r"""print("DEBUG: Sending 'Ro'yxatdan o'tish boshlandi!' message")
\1msg = await message.answer(
\1f"<b>Ro'yxatdan o'tish boshlandi!</b>\""""
content = re.sub(pattern4, replacement4, content)

with open("utils/game_logic.py", "w") as f:
    f.write(content)

print("Patch applied")
