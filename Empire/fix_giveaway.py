import re

with open('/root/empire_ali/Empire/utils/others.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace from_user assignment block
pattern = r"""    sender_user, _ = await User\.get_or_create\(\n        user_id=message\.from_user\.id,\n        defaults=\{"full_name": message\.from_user\.full_name, "mention": message\.from_user\.mention_html\(\)\}\n    \)"""

replacement = r"""    from_user_id = message.from_user.id if message.from_user else ADMINS[0]
    full_name = message.from_user.full_name if message.from_user else "Admin"
    mention = message.from_user.mention_html() if message.from_user else "Admin"
    sender_user, _ = await User.get_or_create(
        user_id=from_user_id,
        defaults={"full_name": full_name, "mention": mention}
    )"""

content = re.sub(pattern, replacement, content, flags=re.DOTALL)

# Update emoji formatting for Qotildan himoya
content = content.replace("⛑️ Qotildan himoya", "<tg-emoji emoji-id='5411452114838761907'>🔪</tg-emoji> Qotildan himoya")
content = content.replace("⛑️ 1 ta", "<tg-emoji emoji-id='5411452114838761907'>🔪</tg-emoji> 1 ta")
content = content.replace("⛑️ Olish", "<tg-emoji emoji-id='5411452114838761907'>🔪</tg-emoji> Olish")
content = content.replace("⛑️ Tabriklaymiz", "<tg-emoji emoji-id='5411452114838761907'>🔪</tg-emoji> Tabriklaymiz")

# Geroy himoya
content = content.replace("🔰 Geroy himoya", "<tg-emoji emoji-id='5334560212986632624'>🔰</tg-emoji> Geroy himoya")
content = content.replace("🔰 1 ta", "<tg-emoji emoji-id='5334560212986632624'>🔰</tg-emoji> 1 ta")
content = content.replace("🔰 Olish", "<tg-emoji emoji-id='5334560212986632624'>🔰</tg-emoji> Olish")
content = content.replace("🔰 Tabriklaymiz", "<tg-emoji emoji-id='5334560212986632624'>🔰</tg-emoji> Tabriklaymiz")

# Sirpanishdan himoya
content = content.replace("🪤 Sirpanishdan himoya", "<tg-emoji emoji-id='5350658016700013471'>🪤</tg-emoji> Sirpanishdan himoya")
content = content.replace("🪤 1 ta", "<tg-emoji emoji-id='5350658016700013471'>🪤</tg-emoji> 1 ta")
content = content.replace("🪤 Olish", "<tg-emoji emoji-id='5350658016700013471'>🪤</tg-emoji> Olish")
content = content.replace("🪤 Tabriklaymiz", "<tg-emoji emoji-id='5350658016700013471'>🪤</tg-emoji> Tabriklaymiz")

# Himoya
content = content.replace("🛡️ Himoya", "<tg-emoji emoji-id='5334560212986632624'>🇺🇿</tg-emoji> Himoya")
content = content.replace("🛡️ 1 ta", "<tg-emoji emoji-id='5334560212986632624'>🇺🇿</tg-emoji> 1 ta")
content = content.replace("🛡️ Olish", "<tg-emoji emoji-id='5334560212986632624'>🇺🇿</tg-emoji> Olish")
content = content.replace("🛡️ Tabriklaymiz", "<tg-emoji emoji-id='5334560212986632624'>🇺🇿</tg-emoji> Tabriklaymiz")

# Update task status in task.md
with open('/root/.gemini/antigravity-ide/brain/ebbf7305-c374-4d30-88f7-a5bb813c485c/task.md', 'r') as f:
    task_content = f.read()

task_content = task_content.replace("- `[/]` `handlers/other_handlers.py` fayliga kanallar", "- `[x]` `handlers/other_handlers.py` fayliga kanallar")
task_content = task_content.replace("- `[ ]` `utils/others.py` faylidagi barcha giveaway xabarlari", "- `[x]` `utils/others.py` faylidagi barcha giveaway xabarlari")

with open('/root/.gemini/antigravity-ide/brain/ebbf7305-c374-4d30-88f7-a5bb813c485c/task.md', 'w') as f:
    f.write(task_content)

with open('/root/empire_ali/Empire/utils/others.py', 'w', encoding='utf-8') as f:
    f.write(content)
